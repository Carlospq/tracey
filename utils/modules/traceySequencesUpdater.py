##############################################################################################################################
#### IMPORTS ####
import subprocess
import xmltodict

##############################################################################################################################
#### FUNCTIONS ####
def get_ncbi_ids(seq):
	fids = seq.foreignannotation.split("|")
	ncbiDictionary = {}
	if len(fids) == 1:
		ncbiDictionary["ncbi_id"] = fids[0].split()[0]
	else:
		for i in range(len(fids)):
			if len(fids[i]) < 4 and fids[i]:
				ncbiDictionary[fids[i]] = fids[i + 1]
	return ncbiDictionary


def esummary(idx, db="protein"):
	# Fetch data from NCBI using esummary
	# db: database to fetch data from
	# id: sequence id
	# Returns: xml data
	# Example: esummary("protein", "NP_001191")
	cmd = "esummary -db %s -id %s"%(db, idx)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	if b'ERROR' in output.upper() or b'Otherdb' in output:
		if b'Invalid db name specified' in output:
			output, error = "", "Invalid db name specified"
		elif b'gi is not found' in output:
			output, error = "", "gi is not found"
		elif b'Otherdb' in output:
			warning = xmltodict.parse(output)['DocumentSummarySet']['Warning']
			output, error = "", "ID %s not found in db '%s', but found in db '%s' with id %s" % (idx, db, warning['Otherdb']['@db'], warning['Otherdb']['@uid'])
		else:
			output, error = "", "Invalid ID format"
	else:
		output = xmltodict.parse(output)['DocumentSummarySet']['DocumentSummary']
	return [output, error]

def efetch(idx, db="sequences"):
	cmd = 'efetch -db %s -id %s -format gb -mode xml' % (db, idx)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	output = xmltodict.parse(output)['GBSet']['GBSeq']
	return [output, error]
##############################################################################################################################