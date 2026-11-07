"""Feature transform shared by training and the event-stream pipeline."""
import numpy as np


def compress(X):
    """Signed log-like compression of relative amplitude changes.
    Changes span 0.05 % (noise) to 70 % (hand on the outer electrode); arcsinh keeps
    small changes linear and squeezes large ones so an RBF-SVM can use both."""
    return np.arcsinh(np.asarray(X) / 5e-4)
