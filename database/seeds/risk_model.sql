-- risk_model.sql
-- Seeds risk model version 'v1' with the weights and thresholds defined in
-- architecture spec §I.3.
--
-- The scoring formula:
--   impact_score = 100
--                × event_severity          (0–1, lookup table by event_type)
--                × dependency_strength     (0–1, multiplicative gate)
--                × evidence_quality        (0–1, multiplicative gate)
--                × (1 + urgency_multiplier)  (0–0.5)
--                × exposure_multiplier     (0.8–1.5)
--
-- event_severity values match arch §I.3.
-- tier_decay values match arch §I.3 dependency_strength formula.
-- Severity bands: CRITICAL ≥75, HIGH 55–74, MEDIUM 35–54, LOW 15–34, below 15 = no alert.

INSERT INTO risk_model_versions (version, weights, thresholds, is_active, activated_at)
VALUES (
    'v1',
    '{
        "event_severity": {
            "sanction_designation":    1.00,
            "export_prohibition":      0.90,
            "insolvency_filing":       0.90,
            "export_restriction":      0.75,
            "quota_imposition":        0.70,
            "facility_disruption":     0.65,
            "credit_downgrade":        0.55,
            "tariff_change":           0.50,
            "regulatory_proposal":     0.30,
            "default":                 0.40
        },
        "tier_decay": {
            "1": 1.00,
            "2": 0.60,
            "3": 0.35,
            "4": 0.20,
            "5": 0.10
        },
        "single_source_boost": 1.3,
        "single_source_cap":   1.0,
        "criticality_formula": "0.5 + 0.5 * criticality / 5",
        "source_reliability": {
            "high":   1.00,
            "medium": 0.75,
            "low":    0.50
        },
        "corroboration_base":  0.70,
        "corroboration_per_source": 0.10,
        "corroboration_cap":   1.00,
        "urgency_multiplier": {
            "in_force_now":  0.50,
            "within_7d":     0.45,
            "within_30d":    0.35,
            "within_90d":    0.20,
            "beyond_90d":    0.10,
            "no_date":       0.15
        },
        "exposure_multiplier": {
            "no_spend_data": 1.00,
            "log_scale_min": 0.80,
            "log_scale_max": 1.50
        },
        "confidence_human_judgment_threshold": 0.50
    }'::jsonb,
    '{
        "CRITICAL": 75,
        "HIGH":     55,
        "MEDIUM":   35,
        "LOW":      15,
        "no_alert": 0
    }'::jsonb,
    true,
    NOW()
)
ON CONFLICT (version) DO UPDATE SET
    weights      = EXCLUDED.weights,
    thresholds   = EXCLUDED.thresholds,
    is_active    = EXCLUDED.is_active,
    activated_at = EXCLUDED.activated_at,
    updated_at   = NOW();
