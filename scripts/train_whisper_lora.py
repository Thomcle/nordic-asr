#!/usr/bin/env python3
"""Fine-tune Whisper with language tags and LoRA on JSONL manifests."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
import torchaudio.functional as AF
from jiwer import wer
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset
from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration,
    WhisperProcessor,
)

class ManifestDataset(Dataset):
    def __init__(self, path: Path, custom_language_tokens: bool = False) -> None:
        with path.open(encoding="utf-8") as handle:
            self.rows = [json.loads(line) for line in handle]
        self.custom_language_tokens = custom_language_tokens

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.rows[index]
        samples, sample_rate = sf.read(row["audio"], dtype="float32", always_2d=False)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        waveform = torch.from_numpy(np.asarray(samples))
        if sample_rate != 16000:
            waveform = AF.resample(waveform, sample_rate, 16000)
        text = row["text"]
        if self.custom_language_tokens:
            text = f"<|{row['language']}|>{text}"
        return {
            "audio": waveform.numpy(),
            "text": text,
        }


@dataclass
class Collator:
    processor: WhisperProcessor

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        audio = [item["audio"] for item in features]
        batch = self.processor.feature_extractor(
            audio, sampling_rate=16000, return_tensors="pt"
        )
        labels = self.processor.tokenizer(
            [item["text"] for item in features],
            padding=True,
            return_tensors="pt",
        )
        label_ids = labels.input_ids.masked_fill(labels.attention_mask.ne(1), -100)
        if (label_ids[:, 0] == self.processor.tokenizer.bos_token_id).all():
            label_ids = label_ids[:, 1:]
        batch["labels"] = label_ids
        return batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--model", default="NbAiLab/nb-whisper-large")
    parser.add_argument(
        "--revision",
        default="8c6249fdeeb4dcd05e5735a4c39640607eb6e4ac",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--lora-rank", type=int, default=32)
    parser.add_argument("--eval-steps", type=int, default=500)
    parser.add_argument("--save-steps", type=int, default=500)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--whisper-language", default="norwegian")
    parser.add_argument("--report-to", default="none")
    parser.add_argument(
        "--custom-language-tokens",
        action="store_true",
        help="Use project-specific ISO language tokens for multilingual experiments.",
    )
    parser.add_argument("--resume-from-checkpoint")
    args = parser.parse_args()

    processor = WhisperProcessor.from_pretrained(args.model, revision=args.revision)
    if args.custom_language_tokens:
        language_tokens = [
            "<|nob|>",
            "<|nno|>",
            "<|sme|>",
            "<|smj|>",
            "<|sma|>",
            "<|fkv|>",
        ]
        processor.tokenizer.add_special_tokens(
            {"additional_special_tokens": language_tokens}
        )
    else:
        processor.tokenizer.set_prefix_tokens(
            language=args.whisper_language,
            task="transcribe",
            predict_timestamps=False,
        )
    model = WhisperForConditionalGeneration.from_pretrained(
        args.model,
        revision=args.revision,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    model.resize_token_embeddings(len(processor.tokenizer))
    model.config.forced_decoder_ids = None
    model.generation_config.language = args.whisper_language
    model.generation_config.task = "transcribe"
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = get_peft_model(
        model,
        LoraConfig(
            task_type="SEQ_2_SEQ_LM",
            r=args.lora_rank,
            lora_alpha=args.lora_rank * 2,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "out_proj"],
        ),
    )
    model.print_trainable_parameters()
    processor.save_pretrained(args.output)

    def compute_metrics(prediction: Any) -> dict[str, float]:
        predictions = prediction.predictions
        labels = prediction.label_ids
        labels[labels == -100] = processor.tokenizer.pad_token_id
        hypotheses = processor.tokenizer.batch_decode(predictions, skip_special_tokens=True)
        references = processor.tokenizer.batch_decode(labels, skip_special_tokens=True)
        return {"wer": wer(references, hypotheses)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output),
        max_steps=args.steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        bf16=True,
        gradient_checkpointing=True,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        logging_steps=20,
        predict_with_generate=True,
        generation_max_length=225,
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        save_total_limit=3,
        dataloader_num_workers=8,
        remove_unused_columns=False,
        report_to=args.report_to,
        ddp_find_unused_parameters=False,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=ManifestDataset(args.train, args.custom_language_tokens),
        eval_dataset=ManifestDataset(args.validation, args.custom_language_tokens),
        data_collator=Collator(processor),
        compute_metrics=compute_metrics,
        processing_class=processor,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(args.output / "best")
    processor.save_pretrained(args.output / "best")


if __name__ == "__main__":
    main()
