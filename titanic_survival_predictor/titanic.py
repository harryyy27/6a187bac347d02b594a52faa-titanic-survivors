import pandas as pd
import numpy as np
import scipy as sp 
import matplotlib.pyplot as plt
import seaborn as sns
import math
import pickle
from sklearn import ensemble, discriminant_analysis, gaussian_process
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from keras import layers, models
from keras.utils.np_utils import to_categorical
from keras.callbacks import ReduceLROnPlateau
#pull data from csv
train= pd.read_csv('./titanic/train.csv',delimiter=',')
test = pd.read_csv('./titanic/test.csv', delimiter=',')
##view data
print(train.head())
print(train.sample(10))
print(train.info())
print(train.describe())

correlation_matrix = train.corr()
print(train.corr())
f, ax = plt.subplots(figsize=(12,9))
sns.heatmap(correlation_matrix,vmax=1,vmin=-1,square=True)
plt.show()
##4Cs of data cleaning - correcting, completing, creating, converting
#null values
print(train.isnull().sum())
##fill null values
train['Age'].fillna(train['Age'].median(),inplace=True)
test['Age'].fillna(train['Age'].median(),inplace=True)
train['Embarked'].fillna(train['Embarked'].mode()[0],inplace=True)
test['Embarked'].fillna(train['Embarked'].mode()[0],inplace=True)

train.drop(columns=['PassengerId','Cabin','Ticket'],inplace = True)
test.drop(columns=['Cabin','Ticket'],inplace = True)
print(train.head())
print(test.head())
train['Family_Size']=train['SibSp']+train['Parch']
test['Family_Size']=test['SibSp']+test['Parch']

train['Loner']=1
test['Loner']=1
train['Loner'].loc[train['Family_Size']>0]=0
test['Loner'].loc[test['Family_Size']>0]=0
train['Title']= train['Name'].str.split(', ', expand=True)[1].str.split(".", expand=True)[0]
test['Title']= test['Name'].str.split(', ', expand=True)[1].str.split(".", expand=True)[0]

train.drop(columns=['Name'],inplace=True)
test.drop(columns=['Name'],inplace=True)

print(train.head())
train_title_count=train['Title'].value_counts()<8
test_title_count=test['Title'].value_counts()<8
train['Title']=train['Title'].apply(lambda x: 'Other' if train_title_count.loc[x]==True else x)
test['Title']=test['Title'].apply(lambda x: 'Other' if test_title_count.loc[x]==True else x)

#other includes all titles bar main 4
print(train['Title'].value_counts())

print(train['Fare'])
sns.distplot(train['Fare'],fit=sp.stats.norm)
fig = plt.figure()
res = sp.stats.probplot(train['Fare'],plot=plt)
plt.show()

zeros = train.loc[train['Fare']==0]
test_zeros = test.loc[test['Fare']==0]
print(zeros)
## NO ZERO VALUES IN TEST FOR FARE
print(test_zeros)
filter_columns = train[['Pclass','Fare']]
filter_free_tickets = filter_columns[filter_columns['Fare']>0]
class_groups = filter_free_tickets.groupby('Pclass')

for name,group in class_groups:
    sns.distplot(group['Fare'])
    plt.show()

class_groups_median= class_groups.median()
print(class_groups_median)
def col_change(x,y):
    if x==0:
        return class_groups_median.iloc[y-1]['Fare']
    else:
        return x
train['Fare']=train.apply(lambda x: col_change(x['Fare'],x['Pclass']), axis=1)
test['Fare']=test.apply(lambda x: col_change(x['Fare'],x['Pclass']),axis=1)
#     test['Fare']=test['Fare'].apply(lambda x: class_groups_median.iloc[i+1,0] if x==0 else x)
new_zeros = train.loc[train['Fare']==0]
new_test_zeros=test.loc[test['Fare']==0]
print(new_zeros)
print(new_test_zeros)
print(train['Fare'])
fare_mean = train['Fare'].mean()
fare_std = train['Fare'].std()
test['Fare']=test['Fare'].apply(lambda x: np.log(x))
test['Fare']-=fare_mean
test['Fare']/=fare_std
train['Fare']=train['Fare'].apply(lambda x: np.log(x))
train['Fare']-=fare_mean
train['Fare']/=fare_std
print(class_groups_median)
sns.distplot(train['Fare'].to_numpy(),fit=sp.stats.norm)
fig = plt.figure()
res = sp.stats.probplot(train['Fare'],plot=plt)
plt.show()

sns.distplot(train['Age'],fit=sp.stats.norm)
fig = plt.figure()
res = sp.stats.probplot(train['Age'],plot=plt)
plt.show()

age_mean = train['Age'].mean()
age_std = train['Age'].std()
train['Age']-=age_mean
train['Age']/=age_std
test['Age']-=age_mean
test['Age']/=age_std
sns.distplot(train['Age'],fit=sp.stats.norm)
fig = plt.figure()
res = sp.stats.probplot(train['Age'],plot=plt)
plt.show()

train=pd.get_dummies(train)
train=pd.get_dummies(train, columns=['Pclass'])
test=pd.get_dummies(test)
test=pd.get_dummies(test,columns=['Pclass'])
print(train.head())

train_y = train['Survived']
# le = LabelEncoder()
# train_y = to_categorical(train_y)
train.drop(['Survived'],axis=1, inplace=True)
train=train.to_numpy()

def build_model():
    model= models.Sequential()
    model.add(layers.Dense(32,activation='relu',input_shape=(train.shape[1],)))
#     model.add(layers.Dense(16, activation='relu'))
    model.add(layers.Dense(2, activation='softmax'))
    model.compile(optimizer='adam', loss='binary_crossentropy',metrics=['accuracy'])
    return model
k=4
num_samples = len(train)//k
num_epochs = 18
ensemble = []
val_data = train[0:200]
val_targets = train_y[0:200]
train_data = train[200:len(train)]
train_targets = train_y[200:len(train_y)]
for i in range(k):
    print('processing model #',i)
    val_data = train[i* num_samples: (i+1)* num_samples]
    val_targets = train_y[i* num_samples: (i+1)* num_samples]

    partial_train_data = np.concatenate(
        [train[:i*num_samples],
        train[(i+1)* num_samples:]],axis=0
    )
    partial_train_targets = np.concatenate(
        [train_y[:i*num_samples],
        train_y[(i+1)* num_samples:]],
        axis=0
    )
    dtrain = xgb.DMatrix(partial_train_data,partial_train_targets)
    dval = xgb.DMatrix(val_data,val_targets)
#     dtrain = xgb.DMatrix(train_data,train_targets)
#     dval = xgb.DMatrix(val_data,val_targets)
    eval_list = [(dval,'eval'),(dtrain,'train')]
    num_round = 25
    params = {
             'max_depth': 4, #maximum number of levels in decision tree
             'objective': 'binary:logistic', #determines loss function used
             'eta':0.125, #learning rate
             'min_child_weight':1, #minimum similarity score for each leaf. if similarity score of leaf<min_child_weight then this leaf will not be included,
             'gamma':1, #added to denominator of loss function to decrease similirity score of leaves to prevent overfitting',
             'delta': 0.75, #L2 regularization term - Ridge regression. Penalizes high slope values as sensitivity to error increases with slope. good when 
             'alpha': 0.4, #L1 regularization term - Lasso regression. Shrinks less important feature coefficients to zero so useful when unnecessarily large number of features
             'eval_metric': 'error',
             'colsample_bytree': 0.8,
            

            }
    bst = xgb.train(params,dtrain,num_round,eval_list,early_stopping_rounds=20)
    pickle.dump(bst,open('xgb'+ str(i) + '.pickle.dat','wb'))
    loaded_model = pickle.load(open("xgb"+str(i)+".pickle.dat", "rb"))
    accuracy = loaded_model.predict(dval,ntree_limit=bst.best_ntree_limit)
    classifications = [0 if x<=0.5 else 1 for x in accuracy ]

    correct = [True if x==y else False for (x,y) in zip(classifications,val_targets)]
    fraction = correct.count(True)/len(correct)
    print(classifications)
    print(val_targets)
    print(fraction)
    ensemble.append(loaded_model)

ensemble = np.array(ensemble)
# indices = np.random.choice(range(0,891),200,replace=False)
# val_dat = []
# val_labels= []
# for i in indices:
#     val_dat.append(train[i])
#     val_labels.append(train_y[i])
passenger_id = test['PassengerId']
test.drop(['PassengerId'],axis=1,inplace=True)

test = test.to_numpy()
print(test[0:5])
final_predictions = []
# for i in range(len(val_dat)):
#     predictions = []
#     for model in ensemble:
#         dval = xgb.DMatrix([val_dat[i]],[val_labels[i]])
#         predict = model.predict(dval)
#         print(predict)
#         prediction = predict[0]
#         if prediction <=0.5:
#             predictions.append(0)
# #         int_prediction = predict[0].tolist().index(prediction)
#         else:
#             predictions.append(1)
#     most_votes = sp.stats.mode(predictions)
#     print(val_labels[i])
#     print(most_votes)
    
#     print(val_labels[i]==most_votes[0][0])
#     if val_labels[i]==most_votes[0][0]:
#         final_predictions.append(True)
#     else:
#         final_predictions.append(False)
for i in range(len(test)):
    predictions = []
    for model in ensemble:
        dtest = xgb.DMatrix([test[i]])
        predict = model.predict(dtest)
        prediction = predict[0]
        if prediction <=0.5:
            predictions.append(0)
#         int_prediction = predict[0].tolist().index(prediction)
        else:
            predictions.append(1)
    most_votes = sp.stats.mode(predictions)
    final_predictions.append([passenger_id[i],most_votes[0][0]])
# val_acc = final_predictions.count(True) / len(final_predictions)
# val_loss = final_predictions.count(False) / len(final_predictions)
# print(val_acc)
# print(val_loss)
# print(test)
# print(train)
print(len(final_predictions))
submission = pd.DataFrame(data=np.array(final_predictions), columns=['PassengerId','Survived'])
print(submission.head())