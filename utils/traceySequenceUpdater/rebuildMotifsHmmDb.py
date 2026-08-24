# Rebuilds utils/hmmModels/MOTIFS.hmmDb (the concatenated + hmmpress-indexed HMM
# database used by motifScan() when proteinlayout == "ALL") from the individual
# .hmm files under utils/hmmModels/<FAMILY>/.
#
# Run standalone:
#   /home/cpulidoq/anaconda3/envs/django/bin/python utils/traceySequenceUpdater/rebuildMotifsHmmDb.py
# Or import rebuild_motifs_hmmdb() from another script/shell session.

import os
import subprocess


def rebuild_motifs_hmmdb(hmm_root='utils/hmmModels', db_name='MOTIFS.hmmDb'):

	db_path = os.path.join(hmm_root, db_name)

	hmm_files = []
	for folder in sorted(os.listdir(hmm_root)):
		folder_path = os.path.join(hmm_root, folder)
		if not os.path.isdir(folder_path):
			continue
		for fname in sorted(os.listdir(folder_path)):
			if fname.endswith('.hmm'):
				hmm_files.append(os.path.join(folder_path, fname))

	with open(db_path, 'w') as out:
		for hmm_file in hmm_files:
			out.write(open(hmm_file).read())

	subprocess.call('hmmpress -f %s' % db_path, shell=True, stdout=open(os.devnull, 'wb'))

	print('Rebuilt %s from %d HMM files.' % (db_path, len(hmm_files)))


if __name__ == "__main__":
	rebuild_motifs_hmmdb()
