# MacCartney and Manning 2009: An extended model of natural logic

Bill MacCartney, Christopher D. Manning. *An extended model of natural logic.* IWCS 2009. Verified 2026-09-29 at https://aclanthology.org/W09-3714/.

## What it says

A model of inference that works directly on natural language expressions with a small set of semantic relations (equivalence, forward and reverse entailment, negation, alternation, cover, independence) and rules for how the relations compose and project through the context. Entailment between phrases is treated as set inclusion and is decided by the edits that turn one phrase into the other.

## Why it matters for DiCo-NLI

The four DiCo-NLI labels are a subset of these relations, and the "edit" view explains the surface cues the EDA found: adding a modifier narrows the set (forward entailment), removing one widens it (backward), and swapping a word for an unrelated one breaks the relation. It also defines what a consistent system must do under reversal, since forward and reverse entailment are each other's converses.

## Where it goes

Assignment 1: the formal background for the labels and for the research question.
