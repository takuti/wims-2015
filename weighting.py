# coding: utf-8

import json
import math

def weighting(resources, assignments):

  # N2 is the number of resource clusters
  N2 = len(set(assignments))

  # set of all tags
  T = set([])

  # compute tag frequencies in each resource cluster
  tf = [{} for ell in range(N2)]
  for i, resource in enumerate(resources):

    ell = assignments[i]

    for tag, freq in resource['tags'].items():
      if not tf[ell].has_key(tag): tf[ell][tag] = 0
      tf[ell][tag] += freq
      T.add(tag) # add tag to the tag set

  # compute inverse document frequency for each tag
  idf = {}
  df = {}
  for t in T:

    df[t] = 0

    for ell in range(N2):
      if tf[ell].has_key(t): df[t] += 1

    # idf_t = max[0, log((N2 - df_t) / df_t)]
    x = (N2 - df[t]) / float(df[t])
    idf[t] = 0. if x < 1. else math.log10(x)

  # compute tag weights in each cluster as: tf * idf,
  # and compute normalized coefficient w0 for each cluster
  w = []
  w0 = []
  for ell in range(N2):

    # create w[ell] and w0[ell]
    w.append({})
    w0.append(0.)

    for t in T:
      if not tf[ell].has_key(t): continue # skip tags which are not in T_ell
      w[ell][t] = tf[ell][t] * idf[t]
      w0[ell] += w[ell][t] ** 2

    w0[ell] = math.sqrt(w0[ell])

  # compute normalized tag weights
  w_s = []
  for ell in range(N2):

    # create w_s[ell]
    w_s.append({})

    for t in T:
      if not tf[ell].has_key(t): continue # skip tags which are not in T_ell
      w_s[ell][t] = w[ell][t] / w0[ell]

  return w_s, tf, df

def main():
  # variables of necessary file pathes
  path_resources = 'dataset/pages.json'
  path_IRM_status = 'dataset/IRM_output/status'
  path_IRM_assignments = 'dataset/IRM_output/page_assignments'

  with open(path_resources) as f:
    resources = json.load(f)

  # 7-th column of the IRM status file is an overall score for the cluster assignments
  statuses = map(lambda l: l.rstrip().split(), open(path_IRM_status).readlines())
  scores = map(lambda status: float(status[6]), statuses)

  # get an index of max-scored cluster assignment
  best_idx = scores.index(max(scores))

  # get best cluster assignment for resources
  assignments = map(int, open(path_IRM_assignments).readlines()[best_idx].rstrip().split(' '))

  w, tf, df = weighting(resources, assignments)
  N2 = len(w)

  # normalized eta(9, ell) in Fig. 7
  eta = [0.1886328, 0.0928793, 0.0275322, 0.0011955, 0.1302496, 0.2343522, 0.0442201, 0.2809383]

  # weights of tags for 9-th user cluster as shown in Fig. 8
  w_9 = {}

  # display Top-3 weighted tags in each cluster, and eta(9, ell)
  print '<<< Top-3 normalized weights >>>'
  for ell in range(N2):
    print '\n--- T_%d [eta(9, %d) = %f]' % (ell+1, ell+1, eta[ell])
    for tag, weight in sorted(w[ell].items(), key=lambda x: -x[1])[:3]:
      print '%.6f (tf=%3d, df=%1d) %s' % (weight, tf[ell][tag], df[tag], tag)

      # compute w_9
      if not w_9.has_key(tag): w_9[tag] = 0
      w_9[tag] += weight * eta[ell]

  print '\n<<< Top-5 weighted tags for 9-th user cluster >>>'
  for tag, weight in sorted(w_9.items(), key=lambda x: -x[1])[:5]:
    print '%.6f %s' % (weight, tag)

if __name__ == '__main__':
  main()
