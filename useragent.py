import os
import sys
import argparse
import re

from sklearn import tree
from indicator_features import indicators as ids
from indicator_features import info_sources as ifs

from indicator_family_table import indicator_family_lv1 as ift1
from indicator_family_table import indicator_family_lv2 as ift2


def read_input_file(file_name):
    ## inputs: [string, family+\t+version]
    inputs = []
    with open(file_name) as f:
        for line in f:
            blocks = line.split('\t')
            curt = []
            curt.append(blocks[0])
            curt.append(blocks[1]+':'+blocks[2])
            inputs.append(curt)
    return inputs


def find_version_by_indicator(other_info, dev_info, indicator, use_other):
    info = other_info if use_other else dev_info
    if indicator=='MSIE' or indicator=='AOL' or indicator=='Android':
        ## special cases: indicator ver.###, found in dev_info
        pos = info.find(indicator)
        return info[info.find(' ', pos)+1 : info.find('.', pos)]
    elif indicator=='rv':
        pos = info.find(indicator)
        return info[info.find(':', pos)+1 : info.find('.', pos)]
    elif indicator=='Safari' and 'Android' in dev_info:
        return find_version_by_indicator(other_info, dev_info, 'Android', False)
    elif indicator=='Safari' and 'GSA' in other_info:
        return None
    elif indicator=='Safari':
        return find_version_by_indicator(other_info, dev_info, 'Version', True)
    elif indicator=='BB':
        pos = info.find(indicator)
        return info[pos+2 : info.find(' ', pos)]
    elif indicator=='BlackBerry':
        return find_version_by_indicator(other_info, dev_info, 'Version', True)
    else:
        ## common cases: indicator/ver.###, found in other_info
        pos = info.find(indicator)
        return info[info.find('/', pos)+1 : info.find('.', pos)]


def correct_family(other_info, dev_info, family):
    if family=='None':
        return None
    if family=='Chrome' and 'Mobile' in other_info:
        return 'Chrome Mobile'
    if family=='Safari' and 'Android' in dev_info:
        return 'Android'
    if family=='Safari' and 'Mobile' in other_info:
        return 'Mobile Safari'
    if family=='Edge' and 'Mobile' in other_info:
        return 'Edge Mobile'
    if family=='Firefox' and dev_info is not None and ('Android' in dev_info or 'Mobile' in dev_info or 'Tablet' in dev_info):
        return 'Firefox Mobile'
    if family=='OPR' and 'Android' in dev_info:
        return 'Opera Mobile'
    if family=='OPR' and 'Opera Mini' in dev_info:
        return 'Opera Mini'
    else:
        return family


def process_string(string):
    dev_info = string[string.find('(')+1:string.find(')')]
    other_info = ' '.join(re.sub('\(.*?\)', '', string).split(' ')[2:])
    return dev_info, other_info


## a directly parsing approach to get the family and version
def get_family_and_version(string):
    [dev_info, other_info] = process_string(string)
    
    family = 'null'
    version = 'null'

    lv1_found = False
    lv2_found = False

    for indicator in ift1:
        infos = ift1[indicator]
        info_source = other_info if infos[1]=='other_info' else dev_info
        if indicator in info_source:
            family = infos[0]
            version = find_version_by_indicator(other_info, dev_info, indicator, infos[1]=='other_info')
            lv1_found = True
        if lv1_found:
            break
    
    if lv1_found:
        return correct_family(other_info, dev_info, family), version

    for indicator in ift2:
        infos = ift2[indicator]
        info_source = other_info if infos[1]=='other_info' else dev_info
        if indicator in info_source:
            family = infos[0]
            version = find_version_by_indicator(other_info, dev_info, indicator, infos[1]=='other_info')
            lv2_found = True
        if lv2_found:
            break

    return correct_family(other_info, dev_info, family), version


## sampling on some specific types of strings to find patterns
## only used during development
'''
def scout(inputs):
    scouts = {}
    for inp in inputs:
        family = inp[1].split(':')[0]
        if 'Android' == family:
            scouts[inp[1]] = inp[0]
    for key in scouts:
        print(key+' : '+scouts[key])
'''


## taking all entries of a specific kind of strings
## only used during development
'''
def check(inputs):
    checks = []
    for inp in inputs:
        family = inp[1].split(':')[0]
        version = inp[1].split(':')[1].strip()
        if 'IE'==family and '11'==version:
            checks.append(inp[0])
    for ent in checks:
        print(ent)
'''


def featurize(string):
    vector = []
    for id in ids:
        if id in string:
            vector.append(1)
        else:
            vector.append(0)
    return vector


def train_model(entries):
    train_classes = []
    train_features = []
    for entry in entries:
        string = entry[0]
        train_features.append(featurize(string))
        [true_family, true_version] = entry[1].split(':')
        train_classes.append(true_family)
    clf = tree.DecisionTreeClassifier()
    clf = clf.fit(train_features, train_classes)
    return clf


def parse_output_file(file_name, entries):
    cnt = 0
    cnt_correct_family = 0
    cnt_correct_version = 0

    with open(file_name, 'w') as f:
        for entry in entries:
            [true_family, true_version] = entry[1].split(':')
            family, version = get_family_and_version(entry[0])
            family = 'null' if family is None else family
            version = 'null' if version is None else version
            f.write(entry[0]+'\t'+true_family+'\t'+true_version+'\t'+family+'\t'+version+'\n')

            cnt += 1
            if(family==true_family):
                cnt_correct_family += 1
            if(str(version).strip()==str(true_version).strip()):
                cnt_correct_version += 1

    print('total number of entries: {}'.format(cnt))
    print('correct families found: {}'.format(cnt_correct_family))
    print('correct versions found: {}'.format(cnt_correct_version))


def predict_output_file(file_name, entries, clf):
    cnt = 0
    cnt_correct_family = 0
    cnt_correct_version = 0

    pred_features = []
    for entry in entries:
        pred_features.append(featurize(entry[0]))
    pred_families = clf.predict(pred_features)

    with open(file_name, 'w') as f:
        for group in zip(entries, pred_families):
            entry = group[0]
            family = group[1]
            [true_family, true_version] = entry[1].split(':')
            [dev_info, other_info] = process_string(entry[0])
            use_other = ifs[family][1]=='other_info'
            version = find_version_by_indicator(other_info, dev_info, ifs[family][0], use_other)
            family = 'null' if family is None else family
            version = 'null' if version is None else version
            f.write(entry[0]+'\t'+true_family+'\t'+true_version+'\t'+family+'\t'+version+'\n')

            cnt += 1
            if(family==true_family):
                cnt_correct_family += 1
            if(str(version).strip()==str(true_version).strip()):
                cnt_correct_version += 1

    print('total number of entries: {}'.format(cnt))
    print('correct families found: {}'.format(cnt_correct_family))
    print('correct versions found: {}'.format(cnt_correct_version))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--learning', type=bool, help='whether to use machine learning approach')
    parser.add_argument('--train', help='specify path of training data')
    parser.add_argument('--test', help='specify path of testing data')
    parser.add_argument('--results', help='specify path of prediction results')

    args = parser.parse_args()
    isLearning = False if args.learning is None else args.learning
    train_path = './data_coding_exercise.txt' if args.train is None else args.train
    test_path = './test_data_coding_exercise.txt' if args.test is None else args.test
    results_path = './pred_data_coding_exercise.txt' if args.results is None else args.results
    sys.path.append(os.path.join(os.path.dirname(__file__), train_path))
    sys.path.append(os.path.join(os.path.dirname(__file__), test_path))
    sys.path.append(os.path.join(os.path.dirname(__file__), results_path))

    trains = read_input_file(train_path)
    tests = read_input_file(test_path)
    if isLearning:
        clf = train_model(trains)
        predict_output_file(results_path, tests, clf)
    else:
        parse_output_file(results_path, tests)