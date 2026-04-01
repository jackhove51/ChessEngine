from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

from dataset.get_dataset import Dataset

dataset = Dataset()


X_train, X_test, y_train, y_test = train_test_split(
    dataset.X, dataset.y, test_size=0.2
)

model = GradientBoostingRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8
)
model.fit(X_train, y_train)
print(model.score(X_test, y_test))