from __future__ import annotations

import logging

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

from dataset.get_dataset import Dataset

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

dataset = Dataset().build()

X_train, X_test, y_train, y_test = train_test_split(
    dataset.X, dataset.y, test_size=0.2, random_state=42
)

model = GradientBoostingRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
)
model.fit(X_train, y_train)

r2 = model.score(X_test, y_test)
logger.info("R² on test set: %.4f", r2)