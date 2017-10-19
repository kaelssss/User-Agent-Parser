User agent parser using 2 different approaches:
direct string parser and decision tree classifier
Tiange(Kevin) Zhao, Oct 18th, 2017

to see help:
python useragent.py -h
to use:
python useragent.py
--learning #True or False indicating whether to use learning approach or parsing approach# 
--train_path #relative path to the training data file#
--test_path #relative path to the testing data file#
--results_path #relative path to the results storing data file#

before using, make sure that:
1. sklearn is installed
2. 'indicator_family_table.py' and 'indicator_features.py' are in the same (or directly reachable) directory of useragent.py
3. prepare the data and test_data txts