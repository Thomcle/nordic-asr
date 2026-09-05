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

LANGUAGE_TOKENS = ["<|nob|>", "<|nno|>", "<|sme|>", "<|smj|>", "<|sma|>", "<|fkv|>"]


class ManifestDataset(Dataset):
    def __init__(self, path: Path) -> None:
        with path.open(encoding="utf-8") as handle:
            self.rows = [json.loads(line) for line in handle]

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
        return {
            "audio": waveform.numpy(),
            "text": f"<|{row['language']}|>{row['text']}",
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
    parser.add_argument("--model", default="openai/whisper-large-v3")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--lora-rank", type=int, default=32)
    args = parser.parse_args()

    processor = WhisperProcessor.from_pretrained(args.model)
    processor.tokenizer.add_special_tokens(
        {"additional_special_tokens": LANGUAGE_TOKENS}
    )
    model = WhisperForConditionalGeneration.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    model.resize_token_embeddings(len(processor.tokenizer))
    model.config.forced_decoder_ids = None
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
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        bf16=True,
        gradient_checkpointing=True,
        eval_strategy="steps",
        eval_steps=500,
        save_steps=500,
        logging_steps=20,
        predict_with_generate=True,
        generation_max_length=225,
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        save_total_limit=3,
        dataloader_num_workers=8,
        remove_unused_columns=False,
        report_to="tensorboard",
        ddp_find_unused_parameters=False,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=ManifestDataset(args.train),
        eval_dataset=ManifestDataset(args.validation),
        data_collator=Collator(processor),
        compute_metrics=compute_metrics,
        processing_class=processor,
    )
    trainer.train()
    trainer.save_model(args.output / "best")
    processor.save_pretrained(args.output / "best")


if __name__ == "__main__":
    main()

