from __future__ import annotations

import logging

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

from dataset.get_dataset import Dataset

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

dataset = Dataset().build()

X_train, X_test, y_train, y_test = train_test_split(
    dataset.X, dataset.y, test_size=0.2, random_state=42
)

model = HistGradientBoostingRegressor(
    max_iter=500,         # equivalent to n_estimators
    max_depth=8,          # deeper trees benefit from the richer feature set
    learning_rate=0.05,
    min_samples_leaf=20,  # regularise against noisy eval labels
    l2_regularization=0.1,
    max_bins=255,         # max resolution for histogram splits
    early_stopping=True,  # stops if val score plateaus; saves time
    validation_fraction=0.1,
    n_iter_no_change=20,
    random_state=42,
)
model.fit(X_train, y_train)

r2 = model.score(X_test, y_test)
logger.info("R² on test set: %.4f", r2)
logger.info("Actual iterations: %d", model.n_iter_)