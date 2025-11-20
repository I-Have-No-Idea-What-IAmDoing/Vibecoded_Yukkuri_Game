import math

class Considerations:
    @staticmethod
    def evaluate(input_val, curve_config):
        curve_type = curve_config.get('curve_type', 'linear')
        slope = curve_config.get('slope', 1.0)
        shift = curve_config.get('shift', 0.0)

        # Normalize inputs generally expected to be 0-100 for stats
        # Output should be 0-1 ideally

        val = float(input_val)

        if curve_type == 'logit':
            # Standard sigmoid-ish: 1 / (1 + e^-x)
            # Map 0-100 to roughly -6 to 6 for full range sigmoid
            normalized = (val - 50) / 10.0
            return 1.0 / (1.0 + math.exp(-(normalized * slope + shift)))

        elif curve_type == 'linear':
            # Simple linear mapping 0-100 -> 0-1
            return min(1.0, max(0.0, (val * slope + shift) / 100.0))

        elif curve_type == 'inverse_linear':
            # 100 -> 0, 0 -> 1
            return min(1.0, max(0.0, 1.0 - ((val * slope + shift) / 100.0)))

        elif curve_type == 'step':
            threshold = 50 + shift
            return 1.0 if val >= threshold else 0.0

        return 0.0
