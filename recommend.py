# coding: utf-8

from weighting import *
from CF import *
import time
import random

n_users = 1017
n_pages = 7000

def is_in(array, n):
  """find n from sorted array
  """
  l = 0
  r = len(array) - 1
  while l <= r:
    mid = (l + r) / 2
    if n == array[mid]: return True
    elif n > array[mid]: l = mid + 1
    else: r = mid - 1
  return False

def evaluate(recommends, tests):
  # count true positives
  # i.e., How many test relations are covered by recommendation?
  TP = 0
  for recommend in recommends:
    if is_in(tests, recommend): TP += 1

  precision = TP / float(len(recommends))
  recall = TP / float(len(tests))

  # return F-measure
  if recall + precision == 0: return 0.
  return (2. * recall * precision) / (recall + precision)

def compute_eta(trains, dom0_assignments, dom1_assignments):

  # number of user cluster
  N1 = len(set(dom0_assignments))

  # number of resource cluster
  N2 = len(set(dom1_assignments))

  eta = [0] * N1
  for k in range(N1):
    eta[k] = [0] * N2

  # how many links exist in (k, ell) block
  for rel in trains:
    ui, ri = rel[0], rel[1]
    k = dom0_assignments[ui]
    ell = dom1_assignments[ri]
    eta[k][ell] += 1

  for k in range(N1):

    eta_ = 0.
    for ell in range(N2):
      s = dom0_assignments.count(k) * dom1_assignments.count(ell)
      eta[k][ell] = eta[k][ell] / float(s)
      eta_ += eta[k][ell]

    # normalize
    for ell in range(N2):
      if eta_ == 0: continue
      eta[k][ell] = eta[k][ell] / eta_

  return eta

def random_recommend(trains, tests, n_recommends):
  """Random recommendation
  """

  # compute average on 5 times
  total_f = 0.
  total_time = 0.
  for random_i in range(5):

    start = time.clock()

    cnt = 0
    recommends = []
    while cnt < n_recommends:
      ui, pi = random.randint(0, n_users-1), random.randint(0, n_pages-1)
      if is_in(trains, (ui, pi)): continue
      recommends.append((ui, pi))
      cnt += 1

    end = time.clock()
    elapsed_time = end - start

    recommends.sort()
    f_measure = evaluate(recommends, tests)
    #print '--- <random> elapsed time: %.3f, F-measure: %.5f' % (elapsed_time, f_measure)

    total_time += elapsed_time
    total_f += f_measure

  return total_time / 5., total_f / 5.

def UMF(trains, tests, resources, user_assignments, page_assignments, th):
  """ User-Model-based Filtering (proposed recommendation algorithm)
  """

  start = time.clock()

  w, tf, df = weighting(resources, page_assignments)
  eta = compute_eta(trains, user_assignments, page_assignments)

  N1 = len(eta)
  N2 = len(eta[0])

  # conpute overall tag weights for each user cluster
  w_k = []
  for k in range(N1):
    w_k.append({})

    for ell in range(N2):
      for tag, weight in w[ell].items():
        if not w_k[k].has_key(tag): w_k[k][tag] = 0
        w_k[k][tag] += weight * eta[k][ell]

  ### UMF procedure
  # search recommend relations based on give threshold value
  recommends = []
  for k in range(N1):
    U_k = [ui for ui in range(n_users) if user_assignments[ui] == k]
    for pi in range(n_pages):
      # compute prediction degree
      P = 0.
      for tag in resources[pi]['tags']:
        P += w_k[k][tag]
      if P > th:
        for ui in U_k:
          if not is_in(trains, (ui, pi)): recommends.append((ui, pi))

  end = time.clock()
  elapsed_time = end - start

  recommends.sort()
  f_measure = evaluate(recommends, tests)

  return elapsed_time, f_measure

def CF(trains, tests, n_recommends):
  """User-based Collaborative Filtering
  """

  user_data = [0.] * n_users
  recommends = []
  n_recommends_per_user = n_recommends / n_users
  for ui in range(n_users):
    user_data[ui] = [0.] * n_pages
  for ui, pi in trains:
    user_data[ui][pi] = 1.

  start = time.clock()
  target_users = [0] # just for a single user

  # pick up test tuples only for target users
  target_users.sort()
  target_tests = []
  for test in tests:
    if not is_in(target_users, test[0]): continue
    target_tests.append(test)
  target_tests.sort()

  for ui in target_users:

    # compute similalities between target user and others
    # based on Jaccard similarity
    users_sims = calc_users_similarity(ui, user_data, sim=jaccard)

    # compute user-item scores for all web pages
    # and sort the results acending order
    tuples = []
    for pi in range(n_pages):
      tuples.append((userbase_scoring(ui, pi, user_data, users_sims), ui, pi))
    tuples.sort()
    tuples.reverse()

    # top-N (N=n_recommends/n_users) will be recommended
    for ri in range(n_recommends_per_user):
      recommends.append((tuples[ri][1], tuples[ri][2]))

  end = time.clock()
  elapsed_time = end - start

  recommends.sort()
  f_measure = evaluate(recommends, target_tests)
  return elapsed_time, f_measure

def main():
  path_resources = 'dataset/pages.json'
  with open(path_resources) as f:
    resources = json.load(f)

  IRM_iter = 2 # which result of IRM iteration will be used
  th = .025 # threshold for UMF

  # 5-fold cross validation
  total = {
      'UMF': {
          'time': 0.,
          'f': 0.
        },
      'Random': {
          'time': 0.,
          'f': 0.
        },
      'CF': {
          'time': 0.,
          'f': 0.
        }
      }
  for fold in range(1, 5+1):

    path_train_relations = 'dataset/5-fold/train/%d_train.graph' % fold
    path_test_relations = 'dataset/5-fold/test/%d_test.graph' % fold
    path_dom0_assignments = 'dataset/5-fold/output/fold%d/dom0' % fold
    path_dom1_assignments = 'dataset/5-fold/output/fold%d/dom1' % fold

    # get an index of max-scored cluster assignment
    """
    path_IRM_status = 'dataset/5-fold/output/fold%d/status' % fold
    statuses = map(lambda l: l.rstrip().split(), open(path_IRM_status).readlines())
    scores = map(lambda status: float(status[6]), statuses)
    best_idx = scores.index(max(scores))
    """

    # get train relations
    lines = map(lambda l: l.rstrip().split(' '), open(path_train_relations).readlines())
    trains = []
    for line in lines:
      trains.append((int(line[1]), int(line[2])))
    trains.sort()

    # get test relations
    lines = map(lambda l: l.rstrip().split(' '), open(path_test_relations).readlines())
    tests = []
    for line in lines:
      tests.append((int(line[1]), int(line[2])))
    tests.sort()

    print '*** fold %d' % fold

    ### Tag-weights-based filstering
    # get cluster assignments for train data
    user_assignments = map(int, open(path_dom0_assignments).readlines()[IRM_iter].rstrip().split(' '))
    page_assignments = map(int, open(path_dom1_assignments).readlines()[IRM_iter].rstrip().split(' '))

    elapsed_time, f_measure = UMF(trains, tests, resources, user_assignments, page_assignments, th)
    total['UMF']['time'] += elapsed_time
    total['UMF']['f'] += f_measure
    print '[UMF] elapsed time: %.3f, F-measure: %.5f' % (elapsed_time, f_measure)

    ### Random recommendation
    elapsed_time, f_measure = random_recommend(trains, tests, 333951)
    total['Random']['time'] += elapsed_time
    total['Random']['f'] += f_measure
    print '[Random (average of 5)] elapsed time: %.3f, F-measure: %.5f' % (elapsed_time, f_measure)

    ### User-based collaborative filtering ([n_recommends / n_user] tuples per a user)
    elapsed_time, f_measure = CF(trains, tests, 333951)
    total['CF']['time'] += elapsed_time
    total['CF']['f'] += f_measure
    print '[CF] elapsed time: %.3f, F-measure: %.5f' % (elapsed_time, f_measure)

  print '*** Result (average of 5-folds)'
  for method, d in total.items():
    print '[%s] elapsed time: %.3f F-measure: %.5f' % (method, d['time'] / 5., d['f'] / 5.)

if __name__ == '__main__':
  main()
