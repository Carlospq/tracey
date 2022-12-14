from apps.home.models import *

sequences = Sequences.objects.all()
with open('utils/ncbi-blast-2.13.0+/tracey.fasta', 'w') as f:
    for seq in sequences:
        foreignannotation = seq.foreignannotation.split(" ")[0].strip()
        shortname = [ "NULL"+str(seq.sequence_id) if seq.sequenceshortname == '' or seq.sequenceshortname == None else seq.sequenceshortname][0].strip()
        fastaID = "|".join([ ">"+shortname, foreignannotation ])[:51]
        seqstr = seq.sequence
        f.write('%s\n%s\n'%(fastaID, seqstr))
