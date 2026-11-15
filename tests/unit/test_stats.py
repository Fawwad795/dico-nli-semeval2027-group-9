"""Tests for paired significance tests and reliability subgroups."""

import json

import pytest

from dico_nli.data import Instance, group_pairs, read_instances
from tests.support import FIXTURE_REFERENCE, requires_data_clone


def _instances():
    return read_instances(FIXTURE_REFERENCE)


def _gold(instances):
    return {instance.instance_id: instance.label for instance in instances}


def _perfect(instances):
    return _gold(instances)


def _wrong(instances):
    cycle = {
        "EQUIVALENCE": "FORWARD_ENTAILMENT",
        "FORWARD_ENTAILMENT": "BACKWARD_ENTAILMENT",
        "BACKWARD_ENTAILMENT": "NEGATIVE_OTHER",
        "NEGATIVE_OTHER": "EQUIVALENCE",
    }
    return {instance.instance_id: cycle[instance.label] for instance in instances}


class TestMetrics:
    def test_perfect_predictions_score_one(self):
        from dico_nli.stats import hard_cons, macro_f1, soft_cons, weighted_f1

        instances = _instances()
        gold = _gold(instances)
        predictions = _perfect(instances)
        pairs = group_pairs(instances)

        assert weighted_f1(gold, predictions) == pytest.approx(1.0)
        assert macro_f1(gold, predictions) == pytest.approx(1.0)
        assert soft_cons(gold, predictions, pairs) == pytest.approx(1.0)
        assert hard_cons(gold, predictions, pairs) == pytest.approx(1.0)

    def test_negative_predictions_are_incompatible_on_reversible_pairs(self):
        from dico_nli.stats import soft_cons

        instances = _instances()
        predictions = {instance.instance_id: "NEGATIVE_OTHER" for instance in instances}

        assert soft_cons(_gold(instances), predictions, group_pairs(instances)) == 0.0

    @requires_data_clone
    def test_metrics_match_official_scorer_on_fixture(self, tmp_path):
        from dico_nli.scoring import score, write_predictions
        from dico_nli.stats import hard_cons, macro_f1, soft_cons, weighted_f1

        instances = _instances()
        gold = _gold(instances)
        predictions = _perfect(instances)
        for instance in instances[:4]:
            predictions[instance.instance_id] = "EQUIVALENCE"
        pairs = group_pairs(instances)

        prediction_path = write_predictions(tmp_path / "predictions.csv", predictions)
        official = score(FIXTURE_REFERENCE, prediction_path, tmp_path / "scores")

        assert weighted_f1(gold, predictions) == pytest.approx(official.weighted_f1)
        report = json.loads(official.report_path.read_text(encoding="utf-8"))
        assert macro_f1(gold, predictions) == pytest.approx(
            report["classification"]["macro_f1"]
        )
        assert soft_cons(gold, predictions, pairs) == pytest.approx(official.soft_cons)
        assert hard_cons(gold, predictions, pairs) == pytest.approx(official.hard_cons)


class TestBootstrapDifference:
    @pytest.mark.parametrize(
        "metric", ["weighted_f1", "macro_f1", "soft_cons", "hard_cons"]
    )
    def test_identical_predictions_give_zero_interval(self, metric):
        from dico_nli.stats import bootstrap_difference

        instances = _instances()
        predictions = _perfect(instances)
        result = bootstrap_difference(
            instances, predictions, predictions, metric, n_resamples=100, seed=13
        )

        assert result == pytest.approx((0.0, 0.0, 0.0))

    def test_same_seed_gives_same_interval(self):
        from dico_nli.stats import bootstrap_difference

        instances = _instances()
        arguments = (instances, _perfect(instances), _wrong(instances), "weighted_f1")

        first = bootstrap_difference(*arguments, n_resamples=200, seed=13)
        second = bootstrap_difference(*arguments, n_resamples=200, seed=13)

        assert first == second

    @pytest.mark.parametrize(
        "metric", ["weighted_f1", "macro_f1", "soft_cons", "hard_cons"]
    )
    def test_perfect_against_wrong_excludes_zero(self, metric):
        from dico_nli.stats import bootstrap_difference

        instances = _instances()
        difference, low, high = bootstrap_difference(
            instances,
            _perfect(instances),
            _wrong(instances),
            metric,
            n_resamples=500,
            seed=13,
        )

        assert difference > 0.0
        assert 0.0 < low <= high

    def test_duplicate_pair_draws_preserve_sample_size(self):
        from dico_nli.stats import bootstrap_difference

        instances = _instances()
        seen_sizes = []

        def sample_size(gold, predictions, pairs):
            seen_sizes.append((len(gold), len(pairs)))
            return 0.0

        bootstrap_difference(
            instances,
            _perfect(instances),
            _wrong(instances),
            sample_size,
            n_resamples=20,
            seed=13,
        )

        expected_pair_count = len(group_pairs(instances))
        # The callable runs once per system for the observed data and each resample.
        # Row counts may vary because negative source pairs have one member, while
        # reversible source pairs have two; the number of sampled source pairs may not.
        assert len(seen_sizes) == 42
        assert all(pair_count == expected_pair_count for _, pair_count in seen_sizes)


class TestMcNemarExact:
    def test_identical_predictions_have_no_discordance(self):
        from dico_nli.stats import mcnemar_exact

        instances = _instances()
        predictions = _perfect(instances)

        assert mcnemar_exact(_gold(instances), predictions, predictions) == (0, 0, 1.0)

    def test_perfect_against_wrong_is_significant(self):
        from dico_nli.stats import mcnemar_exact

        instances = _instances()
        a_wrong_b_right, a_right_b_wrong, p_value = mcnemar_exact(
            _gold(instances), _perfect(instances), _wrong(instances)
        )

        assert a_wrong_b_right == 0
        assert a_right_b_wrong == len(instances)
        assert p_value < 0.05


class TestTagSubgroups:
    def test_overlap_and_length_are_constant_within_unordered_pair(self):
        from dico_nli.stats import tag_subgroups

        instances = _instances()
        tags = tag_subgroups(instances, instances)

        assert set(tags["phrase_overlap"]) == {"both"}
        assert tags.groupby("pair_id")["phrase_overlap"].nunique().max() == 1
        assert tags.groupby("pair_id")["length_bucket"].nunique().max() == 1

    def test_overlap_distinguishes_both_one_and_neither(self):
        from dico_nli.stats import tag_subgroups

        dev = [
            Instance("d1", "p1", "Seen A", "Seen B", "EQUIVALENCE"),
            Instance("d2", "p2", "Seen A", "New C", "NEGATIVE_OTHER"),
            Instance("d3", "p3", "New D", "New E", "NEGATIVE_OTHER"),
        ]
        train = [Instance("t1", "t1", "seen a", "seen b", "EQUIVALENCE")]

        tags = tag_subgroups(dev, train, length_bucket_boundaries=(3, 4))

        assert tags.set_index("instance_id")["phrase_overlap"].to_dict() == {
            "d1": "both",
            "d2": "one",
            "d3": "neither",
        }

    def test_reuses_length_cue_annotation(self):
        from dico_nli.analysis import analyze_predictions
        from dico_nli.stats import tag_subgroups

        instances = _instances()
        expected = analyze_predictions(instances, _perfect(instances))[1].set_index(
            "instance_id"
        )["cue_status"]
        actual = tag_subgroups(instances, []).set_index("instance_id")["cue_status"]

        assert actual.to_dict() == expected.to_dict()


class TestScoreSubgroups:
    def test_scores_each_system_and_group(self):
        from dico_nli.stats import score_subgroups, tag_subgroups

        instances = _instances()
        tags = tag_subgroups(instances, [], length_bucket_boundaries=(5, 8))
        scores = score_subgroups(
            instances,
            {"perfect": _perfect(instances), "wrong": _wrong(instances)},
            tags,
            "length_bucket",
        )

        assert set(scores["system"]) == {"perfect", "wrong"}
        assert set(scores["subgroup"]) == set(tags["length_bucket"])
        assert (scores.loc[scores["system"] == "perfect", "accuracy"] == 1.0).all()
        assert (scores.loc[scores["system"] == "wrong", "accuracy"] == 0.0).all()

    def test_rejects_missing_tags(self):
        from dico_nli.stats import score_subgroups, tag_subgroups

        instances = _instances()
        tags = tag_subgroups(instances, []).iloc[:-1]

        with pytest.raises(ValueError, match="tag ids differ"):
            score_subgroups(
                instances, {"perfect": _perfect(instances)}, tags, "phrase_overlap"
            )
