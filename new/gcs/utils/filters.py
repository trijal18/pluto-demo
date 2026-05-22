import math
import time

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

class OneEuroFilter:
    """
    Adaptive Low-Pass Filter for noisy human input.
    Balances jitter reduction (low speed) and lag reduction (high speed).
    """
    def __init__(self, min_cutoff=1.0, beta=0.007, d_cutoff=1.0, initial_value=1500):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        
        self.x_prev = float(initial_value)
        self.dx_prev = 0.0
        self.t_prev = time.time()

    @property
    def value(self):
        return int(self.x_prev)

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def apply(self, x):
        t_now = time.time()
        dt = t_now - self.t_prev
        if dt <= 0: return int(self.x_prev)

        # 1. Filter the derivative (velocity) to compute adaptive cutoff
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        
        # 2. Filter the signal
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self.x_prev
        
        # Update state
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t_now
        
        return int(x_hat)

    def reset(self, value=1500):
        self.x_prev = float(value)
        self.dx_prev = 0.0
        self.t_prev = time.time()
