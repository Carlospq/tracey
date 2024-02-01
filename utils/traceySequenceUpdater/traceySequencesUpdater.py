##############################################################################################################################
import os, subprocess
import xmltodict
import pandas as pd
from apps.home.models import *
##############################################################################################################################
def getCSVname(taxId):
	if taxId == 1:
		return 0
	files = sorted([int(x.split(".csv")[0]) for x in os.listdir('NCBI_update/release221/catalog/')])
	for i in range(len(files)):
		if taxId < files[i]:
			return files[i-1]
	return files[i]


def csvToPd(csv):
	# Catalog path
	catalogPath = 'NCBI_update/release221/catalog/%s.csv' % csv
	# read csv
	header = ["taxonomyId", "speciesName", "accessionVersion", "refseqRelease", "refseqStatus", "length"]
	data = pd.read_csv(catalogPath, sep='\t', header=None, names=header)
	return data


def readRemovedRecordsToPd(removedRecords = 'release221.removed-records'):
	# Removed-records path
	removedRecordsPath = 'NCBI_update/release221/%s' % removedRecords
	# read csv
	header = ['taxonomyId', 'speciesName', 'accessionVersion', 'refseqRelease', 'refseqStatus', 'length', 'removedStatus']
	data = pd.read_csv(removedRecordsPath, sep='\t', header=None, names=header)
	return data
##############################################################################################################################
# All sequences with SNARE/Habc motifs
snareMotifsIds = set([m.sequence_id for m in Motifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])
snareVerifymotifsIds = set([m.sequence_id for m in Verifymotifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])

snareSeqs = Sequences.objects.filter(sequence_id__in=list(snareMotifsIds | snareVerifymotifsIds))
snareSeqsNCBI = snareSeqs.filter(sourcedatabase__in = ['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])	#83304 sequences

# possibles source IDs: ['gi', 'gb', 'emb', 'ref', 'dbj', 'pir', 'prf', 'sp', 'pdb', 'tpe', 'none', 'tpg']
seqIDs = {}
for seq in snareSeqsNCBI:
	fids = seq.foreignannotation.split("|")
	if fids[0] == "none":
		print("ERROR with seq ID %s"%(seq.sequence_id))
		continue
	seqIDs[seq.sequence_id] = {}
	if len(fids) == 1:
		seqIDs[seq.sequence_id]["ncbi_id"] = fids[0].split()[0]
	else:
		for i in range(len(fids)):
			if len(fids[i]) < 4 and fids[i]:
				seqIDs[seq.sequence_id][fids[i]] = fids[i+1]

# tracey SeqIDs without any ID
[x for x in seqIDs if not seqIDs[x]]

# Check ncbi data for each seqID
with open('./NCBI_update/traceySequenceIDsToAnalyze.txt', 'w') as fo:
	for idx in seqIDs:
		found = 0
		for idxtype in ['gi', 'ref', 'gb', 'emb', 'dbj', 'pir', 'prf', 'sp', 'tpe', 'none', 'tpg']:
			if idxtype in seqIDs[idx]:
				if seqIDs[idx][idxtype]:
					found = 1
					if seqIDs[idx][idxtype] == '56539046':
						print(idx, seqIDs[idx])
					fo.write('%s\n'%seqIDs[idx][idxtype])
					break
		if not found:
			print("ERROR with seq ID %s"%(idx))

# fetch ncbi dataset
cmd = 'efetch -db protein -input %s -format gb -mode xml' % './NCBI_update/traceySequenceIDsToAnalyze.txt'
process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

# convert xml to dict
data = xmltodict.parse(output)
with open('./NCBI_update/traceySequenceIDsToAnalyze.txt') as fd:
    data = xmltodict.parse(fd.read())
print(data['GBSet']['GBSeq'])














###


with open('./NCBI_update/traceyIDs/traceyIDs.txt', 'w') as fo:
	for seq in snareSeqsNCBI:
		foreignannotation = seq.foreignannotation.split("|")
		if foreignannotation[0] == "gi":
			sIdx = foreignannotation[1]
			n += 1
			fo.write("%s\n"%sIdx)

with open('./NCBI_update/traceyIDs/missingGI.txt', 'w') as fo:
	for seq in snareSeqsNCBI:
		foreignannotation = seq.foreignannotation.split("|")
		if not foreignannotation[0] == "gi":
			fo.write(str(seq.sequence_id)+"\t"+seq.foreignannotation+"\n")




ncbi_seqs = Sequences.objects.filter(sourcedatabase__in = ['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])
snareseqs = ncbi_seqs.filter(sequence_id__in = snareMotifsIds)

tags = []
for s in snareseqs:
	fa = s.foreignannotation.split("|")
	if len(fa) > 1:
		tags.append(fa[2]



with open('traceyIDs/traceyIDs.txt', 'w') as fo:
	for s in ncbi_seqs_sorted:
		try:
			accession = s.foreignannotation.split("|")[3]
		except IndexError:
			accession = "unknown"
		fo.write("%s\t%s\n" % (s.sequence_id, accession))


# split tracey ID into multiple files with 10000 ids in each file
# split -l 10000 traceyIDs/traceyIDs.txt


#datasets summary gene gene-id
#datasets summary gene symbol
#datasets summary gene accesion

# SPLIT catalog in multiple files
nids = 0
firstid = 0
lastid = 0
nlines = 0
maxlines = 5000000
maxExcided = 0
changeFile = 0
for line in open('NCBI_update/release221/release221.catalog'):
	nlines += 1
	# Switcher for maxlines
	if nlines > maxlines:
		maxExcided = 1
	# Get firstid/lastid for first line in file
	if firstid == 0:
		firstid = line.strip().split()[0]
		lastid = firstid
		fo_name = 'NCBI_update/release221/catalog/%s.csv' % firstid
		fo = open(fo_name, 'w')
	# Get current id very time a new id is found
	if lastid != line.strip().split()[0]:
		if maxExcided:
			changeFile = 1
			maxExcided = 0
		nids += 1
	# Open new file when maxlines is excided or when a max nids is reached
	#if nids > 153 or changeFile:
	if changeFile:
		print("firstid: %s; lastid: %s" % (firstid, lastid))
		nids = 0
		nlines = 0
		changeFile = 0
		firstid = line.strip().split()[0]
		fo_name = 'NCBI_update/release221/catalog/%s.csv' % firstid
		fo = open(fo_name, 'w')
	lastid = line.strip().split()[0]
	_ = fo.write(line)


# SEARCH for tracey ID in current version and removed
# IDs in current version
# for catalogFile in $(ls catalog); do echo $catalogFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]; next} $2 in ids' catalog/$catalogFile traceyIDs/$traceyIdsFile >> traceyIDsInNCBI_Bash.txt; done; done;

# IDs removed
#for removedFile in $(ls removed);    do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$7; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/ $removedFile traceyIDs/ $traceyIdsFile >> traceyIDsRemovedNCBI_Bash.txt; done; done
for removedFile in release10.removed-records   release206.removed-records  release221.removed-records  release38.removed-records  release53.removed-records  release69.removed-records  release84.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash1.txt; done; done
for removedFile in release11.removed-records   release207.removed-records  release23.removed-records   release39.removed-records  release54.removed-records  release7.removed-records   release85.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash2.txt; done; done
for removedFile in release12.removed-records   release208.removed-records  release24.removed-records   release4.removed-records   release55.removed-records  release70.removed-records  release86.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash3.txt; done; done
for removedFile in release13.removed-records   release209.removed-records  release25.removed-records   release40.removed-records  release56.removed-records  release71.removed-records  release87.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash4.txt; done; done

for removedFile in release14.removed-records   release21.removed-records   release26.removed-records   release41.removed-records  release57.removed-records  release72.removed-records  release88.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash5.txt; done; done
for removedFile in release15.removed-records   release210.removed-records  release27.removed-records   release42.removed-records  release58.removed-records  release73.removed-records  release89.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash6.txt; done; done
for removedFile in release16.removed-records   release211.removed-records  release28.removed-records   release43.removed-records  release59.removed-records  release74.removed-records  release9.removed-records; do echo $removedFile;  for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash7.txt; done; done
for removedFile in release17.removed-records   release212.removed-records  release29.removed-records   release44.removed-records  release6.removed-records   release75.removed-records  release90.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash8.txt; done; done

for removedFile in release18.removed-records   release213.removed-records  release3.removed-records    release45.removed-records  release60.removed-records  release76.removed-records  release91.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash9.txt; done; done
for removedFile in release19.removed-records   release214.removed-records  release30.removed-records   release46.removed-records  release61.removed-records  release77.removed-records  release92.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash10.txt; done; done
for removedFile in release20.removed-records   release215.removed-records  release31.removed-records   release47.removed-records  release62.removed-records  release78.removed-records  release93.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash11.txt; done; done
for removedFile in release200.removed-records  release216.removed-records  release32.removed-records   release48.removed-records  release63.removed-records  release79.removed-records  release94.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash12.txt; done; done

for removedFile in release201.removed-records  release217.removed-records  release33.removed-records   release49.removed-records  release64.removed-records  release8.removed-records   release95.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash13.txt; done; done
for removedFile in release202.removed-records  release218.removed-records  release34.removed-records   release5.removed-records   release65.removed-records  release80.removed-records  release96.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash14.txt; done; done
for removedFile in release203.removed-records  release219.removed-records  release35.removed-records   release50.removed-records  release66.removed-records  release81.removed-records  release97.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash15.txt; done; done
for removedFile in release204.removed-records  release22.removed-records   release36.removed-records   release51.removed-records  release67.removed-records  release82.removed-records  release98.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash16.txt; done; done
for removedFile in release205.removed-records  release220.removed-records  release37.removed-records   release52.removed-records  release68.removed-records  release83.removed-records  release99.removed-records; do echo $removedFile; for traceyIdsFile in $(ls traceyIDs); do awk -F"\t" 'NR==FNR {ids[$3]=$0; next} {OFS="\t"; if ($2 in ids) print $1, $2, ids[$2]}' removed/$removedFile traceyIDs/$traceyIdsFile >> traceyIDsRemovedNCBI_Bash17.txt; done; done

cat traceyIDsRemovedNCBI_Bash* >> traceyIDsRemovedNCBI_Bash.txt



# > IDs uknown are either gene IDs or protein version IDs not matching with the version in catalog/removed
# make script to solve this search
for traceyIdsFile in $(ls traceyIDs); do echo $traceyIdsFile; awk -F"\t" 'NR==FNR {ids[$2]=$0; next} {OFS="\t"; print ($2 in ids) ? "#" : $0}' traceyIDsInNCBI_Bash.txt traceyIDs/$traceyIdsFile | grep -v "#" >> IDsNotInTracey.txt; done
awk -F"\t" 'NR==FNR {ids[$2]=$0; next} {OFS="\t"; print ($2 in ids) ? "#" : $0}' traceyIDsRemovedNCBI_Bash.txt IDsNotInTracey.txt | grep -v "#" >> traceyIDsUnknown.txt



for line in open('./NCBI_update/release221/traceyIDsUnknown.txt', 'r'):
	line = line.strip().split("\t")
	s = Sequences.objects.filter(sequence_id=line[0])
	if len(line) <= 1:
		with open('./NCBI_update/release221/traceyIDsUnknownMissingProtId.txt', 'a') as fo:
			foreignannotation = s.foreignannotation.split("|")
			if foreignannotation[0] == "gi":
				gi = foreignannotation[1]
			else:
				gi = "unknown"
	elif line[1][2] == "_":




		s = Sequences.objects.filter(sequence_id=line[0])
		foreignannotation =  s.foreignannotation.split("|")
		if foreignannotation[0] == "gi":
			gID = foreignannotation[1]
		else:
			gID = "unknown"
		fo.write("\t".join([line[0], gID])+"\n")





# Import required entrepy modules
import entrezpy
import entrezpy.conduit
import entrezpy.base.result
import entrezpy.base.analyzer

c = entrezpy.conduit.Conduit('carlos.pulidoquetglas@unil.ch')
fetch_docsum = c.new_pipeline()
sid = fetch_docsum.add_search({'db': 'protein', 'term': 'NP_005810,NP_003756'})
fetch_docsum.add_summary({'rettype':'docsum', 'retmode':'json'}, dependency=sid, analyzer=DocsumAnalyzer())
docsums = c.run(fetch_docsum).get_result().docsums
for i in docsums:
	print(i, docsums[i].uid, docsums[i].caption,docsums[i].strain, docsums[i].subtype.host)













































Format Examples

  -db            -format            -mode    Report Type
  ___            _______            _____    ___________

  (all)
                 docsum                      DocumentSummarySet XML
                 docsum             json     DocumentSummarySet JSON
                 full                        Same as native except for mesh
                 uid                         Unique Identifier List
                 url                         Entrez URL
                 xml                         Same as -format full -mode xml

  bioproject
                 native                      BioProject Report
                 native             xml      RecordSet XML

  biosample
                 native                      BioSample Report
                 native             xml      BioSampleSet XML

  biosystems
                 native             xml      Sys-set XML

  clinvar
                 variation                   Older Format
                 variationid                 Transition Format
                 vcv                         VCV Report
                 clinvarset                  RCV Report

  gds
                 native             xml      RecordSet XML
                 summary                     Summary

  gene
                 full_report                 Detailed Report
                 gene_table                  Gene Table
                 native                      Gene Report
                 native             asn.1    Entrezgene ASN.1
                 native             xml      Entrezgene-Set XML
                 tabular                     Tabular Report

  homologene
                 alignmentscores             Alignment Scores
                 fasta                       FASTA
                 homologene                  Homologene Report
                 native                      Homologene List
                 native             asn.1    HG-Entry ASN.1
                 native             xml      Entrez-Homologene-Set XML

  mesh
                 full                        Full Record
                 native                      MeSH Report
                 native             xml      RecordSet XML

  nlmcatalog
                 native                      Full Record
                 native             xml      NLMCatalogRecordSet XML

  pmc
                 bioc                        PubTator Central BioC XML
                 medline                     MEDLINE
                 native             xml      pmc-articleset XML

  pubmed
                 abstract                    Abstract
                 bioc                        PubTator Central BioC XML
                 medline                     MEDLINE
                 native             asn.1    Pubmed-entry ASN.1
                 native             xml      PubmedArticleSet XML

  (sequences)
                 acc                         Accession Number
                 est                         EST Report
                 fasta                       FASTA
                 fasta              xml      TinySeq XML
                 fasta_cds_aa                FASTA of CDS Products
                 fasta_cds_na                FASTA of Coding Regions
                 ft                          Feature Table
                 gb                          GenBank Flatfile
                 gb                 xml      GBSet XML
                 gbc                xml      INSDSet XML
                 gene_fasta                  FASTA of Gene
                 gp                          GenPept Flatfile
                 gp                 xml      GBSet XML
                 gpc                xml      INSDSet XML
                 gss                         GSS Report
                 ipg                         Identical Protein Report
                 ipg                xml      IPGReportSet XML
                 native             text     Seq-entry ASN.1
                 native             xml      Bioseq-set XML
                 seqid                       Seq-id ASN.1

  snp
                 json                        Reference SNP Report

  sra
                 native             xml      EXPERIMENT_PACKAGE_SET XML
                 runinfo            xml      SraRunInfo XML

  structure
                 mmdb                        Ncbi-mime-asn1 strucseq ASN.1
                 native                      MMDB Report
                 native             xml      RecordSet XML

  taxonomy
                 native                      Taxonomy List
                 native             xml      TaxaSet XML


{"header":{"type":"esummary","version":"0.3"},
 "result":{"uids":["34902878"],
 		   "34902878":{"uid":"34902878",
		   			   "term":"34902878",
					   "caption":"NP_912786",
					   "accessionversion":"NP_912786.1",
					   "sourcedb":"refseq",
					   "title":"unnamed protein product [Oryza sativa (japonica cultivar-group)]",
					   "extra":"gi|34902878|ref|NP_912786.1|",
					   "gi":34902878,
					   "createdate":"2003/09/22",
					   "updatedate":"2004/11/16",
					   "genome":"genomic",
					   "organism":"Oryza sativa (japonica cultivar-group)",
					   "taxid":39947,
					   "geneticcode":"1",
					   "subtype":"cultivar",
					   "subname":"Nipponbare",
					   "slen":280,"moltype":"aa",
					   "topology":"linear",
					   "biomol":"peptide",
					   "assemblygi":5922624,
					   "assemblyacc":"BAA84625",
					   "biosample":"",
					   "statistics":[{"type":"Length","count":280},
					   				 {"type":"pub","count":1},
									 {"type":"Length","subtype":"literal","count":280},
									 {"type":"all","count":1},{"type":"prot","count":1}],
					   "comment":"This whole-genome-shotgun sequence record was removed because it has been superceded by a new assembly of the genome.",
					   "status":"suppressed",
					   "flags":512,
					   "properties":{"aa":"2","value":"2"},
					   "oslt":{"indexed":false,"value":"NP_912786.1"},
					   "idgiclass":{"mol":"3",
					   				"repr":"2",
									"gi_state":"10",
									"sat":"4",
									"sat_key":"7590681",
									"owner":"52",
									"sat_name":"NCBI",
									"owner_name":"NCBI-TTG-MRNA",
									"defdiv":"CON",
									"length":"280",
									"extfeatmask":"0"}}}}


{"header":{"type":"esummary","version":"0.3"},
"result":{"uids":["50549317"],
		  "50549317":{"uid":"50549317",
		  			  "term":"50549317",
					  "caption":"XP_502129",
					  "accessionversion":"XP_502129.1",
					  "sourcedb":"refseq",
					  "title":"hypothetical protein [Yarrowia lipolytica CLIB122]",
					  "extra":"gi|50549317|ref|XP_502129.1|",
					  "gi":50549317,
					  "createdate":"2004/07/23",
					  "updatedate":"2008/03/21",
					  "organism":"Yarrowia lipolytica CLIB122",
					  "taxid":284591,
					  "geneticcode":"1",
					  "subtype":"chromosome|note|strain|old_name",
					  "subname":"C|Genoscope sequence ID : YALI0CCHR|CLIB122|Yarrowia lipolytica CLIB122",
					  "slen":218,
					  "moltype":"aa",
					  "topology":"linear",
					  "biomol":"peptide",
					  "assemblygi":49647996,
					  "assemblyacc":"CAG82449",
					  "biosample":"",
					  "statistics":[{"type":"Length","count":218},
					  				{"type":"pub","count":2},
									{"type":"Length","subtype":"literal","count":218},
									{"type":"all","count":1},
									{"type":"prot","count":1}],
					  "comment":"This sequence has been updated.",
					  "status":"replaced",
					  "replacedby":"XP_502129.2",
					  "flags":512,
					  "properties":{"aa":"2","value":"2"},
					  "oslt":{"indexed":false,"value":"XP_502129.1"},
					  "idgiclass":{"mol":"3",
					  			   "repr":"2",
								   "gi_state":"0",
								   "sat":"17",
								   "sat_key":"95509803",
								   "owner":"28",
								   "sat_name":"OLD12",
								   "owner_name":"NCBI-ContigMRNA",
								   "defdiv":"CON",
								   "length":"218",
								   "extfeatmask":"0"}}}}


{"header":{"type":"esummary","version":"0.3"},
 "result":{"uids":["28933465"],
		   "28933465":{"uid":"28933465",
					   "term":"28933465",
					   "caption":"NP_803173",
					   "title":"syntaxin-12 [Homo sapiens]",
					   "extra":"gi|28933465|ref|NP_803173.1|",
					   "gi":28933465,
					   "createdate":"2003/03/13",
					   "updatedate":"2023/03/12",
					   "flags":512,
					   "taxid":9606,
					   "slen":276,
					   "biomol":"",
					   "moltype":"aa",
					   "topology":"linear",
					   "sourcedb":"refseq",
					   "segsetsize":"",
					   "projectid":"0",
					   "genome":"genomic",
					   "subtype":"chromosome|map",
					   "subname":"1|1p35.3",
					   "assemblygi":"",
					   "assemblyacc":"",
					   "tech":"",
					   "completeness":"",
					   "geneticcode":"1",
					   "strand":"",
					   "organism":"Homo sapiens",
					   "strain":"",
					   "statistics":[{"type":"all","count":8},
					 				 {"type":"blob_size","count":51742},
								   	 {"type":"org","count":1},
								   	 {"type":"prot","count":1},
								     {"type":"prot","subtype":"Prot","count":1},
								   	 {"type":"pub","count":10},
								   	 {"type":"pub","subtype":"PubMed","count":8},
								   	 {"type":"pub","subtype":"PubMed/Gene-rif","count":2},
								   	 {"type":"site","count":6},
								   	 {"type":"site","subtype":"Site","count":6},
								   	 {"source":"CCDS","type":"all","count":2},
								   	 {"source":"CCDS","type":"cdregion","count":1},
								   	 {"source":"CCDS","type":"cdregion","subtype":"CDS","count":1},
								   	 {"source":"CCDS","type":"gene","count":1},
								   	 {"source":"CCDS","type":"gene","subtype":"Gene","count":1},
								   	 {"source":"SNP","type":"VDB","count":1},
								   	 {"source":"SNP","type":"VDB","subtype":"NA000146873.19#17","count":1},
								   	 {"source":"SNP","type":"all","count":1},
								   	 {"source":"all","type":"VDB","count":1},
								   	 {"source":"all","type":"all","count":11},
								   	 {"source":"all","type":"blob_size","count":51742},
								     {"source":"all","type":"cdregion","count":1},
								     {"source":"all","type":"gene","count":1},
								   	 {"source":"all","type":"org","count":1},
								   	 {"source":"all","type":"prot","count":1},
								   	 {"source":"all","type":"pub","count":10},
								   	 {"source":"all","type":"site","count":6}],
					   "properties":{"aa":"2","value":"2"},
					   "oslt":{"indexed":true,"value":"NP_803173.1"},
					   "accessionversion":"NP_803173.1"}}}
