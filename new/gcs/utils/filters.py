class LowPassFilter:
    """
    A simple Exponential Moving Average (EMA) Low-Pass Filter.
    Formula: y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
    """
    def __init__(self, alpha=0.35, initial_value=1500):
        self.alpha = alpha
        self.value = initial_value

    def apply(self, new_value):
        self.value = (self.alpha * new_value) + (1 - self.alpha) * self.value
        return int(self.value)

    def reset(self, value=1500):
        self.value = value
