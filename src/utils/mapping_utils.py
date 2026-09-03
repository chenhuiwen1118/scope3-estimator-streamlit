#!/usr/bin/env python3
"""Shared helpers for activity-to-process mapping workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from pathlib import Path
import os

os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from auto_footprint import (
    ActivityRecord as EvalActivityRecord,
    ImpactConfig,
    evaluate_records,
)
from process_index import open_derby


@dataclass
class ActivityInput:
    label: str
    quantity: float
    unit: str


@dataclass
class ProcessCandidate:
    dataset: str
    process_uuid: str
    process_name: str
    reference_flow: Optional[str]
    location: Optional[str]
    category: Optional[str]

    @property
    def descriptor(self) -> str:
        sections = [self.process_name]
        if self.reference_flow and self.reference_flow not in self.process_name:
            sections.append(self.reference_flow)
        if self.location:
            sections.append(f"Location: {self.location}")
        if self.category:
            sections.append(f"Category: {self.category}")
        sections.append(f"Dataset: {self.dataset}")
        return " | ".join(sections)


def parse_activities_dataframe(
    df: pd.DataFrame,
    item_column: str,
    quantity_column: str,
    unit_column: str,
) -> List[ActivityInput]:
    missing = [col for col in (item_column, quantity_column, unit_column) if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    records: List[ActivityInput] = []
    for _, row in df.iterrows():
        label = str(row[item_column]).strip()
        if not label:
            continue
        try:
            quantity = float(row[quantity_column])
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for item '{label}': {row[quantity_column]!r}") from None
        unit = str(row[unit_column]).strip() or "-"
        records.append(ActivityInput(label=label, quantity=quantity, unit=unit))
    return records


def load_activities_from_excel(
    excel_path,
    sheet: Optional[str],
    item_column: str,
    quantity_column: str,
    unit_column: str,
) -> List[ActivityInput]:
    sheet_name = 0 if sheet is None else sheet
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    return parse_activities_dataframe(df, item_column, quantity_column, unit_column)


def fetch_process_candidates(
    dataset_paths: Sequence[str],
    password: Optional[str],
) -> List[ProcessCandidate]:
    candidates: List[ProcessCandidate] = []
    for dataset in dataset_paths:
        dataset_path = Path(dataset).resolve()
        with open_derby(dataset_path, password) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.REF_ID,
                       p.NAME,
                       flow.NAME,
                       loc.NAME,
                       cat.NAME
                FROM TBL_PROCESSES p
                LEFT JOIN TBL_EXCHANGES exch ON exch.ID = p.F_QUANTITATIVE_REFERENCE
                LEFT JOIN TBL_FLOWS flow ON flow.ID = exch.F_FLOW
                LEFT JOIN TBL_LOCATIONS loc ON loc.ID = p.F_LOCATION
                LEFT JOIN TBL_CATEGORIES cat ON cat.ID = p.F_CATEGORY
                """
            )
            for ref_id, name, ref_flow, location, category in cursor.fetchall():
                candidates.append(
                    ProcessCandidate(
                        dataset=str(dataset_path),
                        process_uuid=str(ref_id),
                        process_name=str(name),
                        reference_flow=str(ref_flow) if ref_flow is not None else None,
                        location=str(location) if location is not None else None,
                        category=str(category) if category is not None else None,
                    )
                )
            cursor.close()
    return candidates


def embed_texts(
    model: SentenceTransformer,
    texts: Sequence[str],
    batch_size: int = 64,
) -> np.ndarray:
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=len(texts) > 200,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype=np.float32)


def rank_candidates(
    activity_embedding: np.ndarray,
    process_embeddings: np.ndarray,
    topk: int,
) -> List[Tuple[int, float]]:
    scores = np.dot(process_embeddings, activity_embedding)
    top_indices = np.argsort(scores)[::-1][:topk]
    return [(int(idx), float(scores[idx])) for idx in top_indices]


def build_activity_records(
    selections: Iterable[Tuple[ActivityInput, ProcessCandidate]],
) -> List[EvalActivityRecord]:
    records: List[EvalActivityRecord] = []
    for activity, candidate in selections:
        records.append(
            EvalActivityRecord(
                activity_id=activity.label,
                quantity=activity.quantity,
                unit=activity.unit,
                process_uuid=candidate.process_uuid,
                dataset_path=Path(candidate.dataset),
                emission_factor=None,
                factor_unit="",
            )
        )
    return records


def evaluate_selections(
    selections: Iterable[Tuple[ActivityInput, ProcessCandidate]],
    password: Optional[str],
    impact_cfg: Optional[ImpactConfig],
    cost_cfg: Optional[ImpactConfig] = None,
):
    records = build_activity_records(list(selections))
    return evaluate_records(records, password, impact_cfg, cost_cfg)
