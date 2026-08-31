# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import xml.etree.ElementTree as ET
import re

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import admin

# Create your models here.
class Analysislevels(models.Model):
    analysislevel_id = models.AutoField(db_column='analysisLevel_id', primary_key=True)  # Field name made lowercase.
    name = models.TextField(db_collation='latin1_swedish_ci')
    comments = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    level = models.IntegerField(unique=True)

    class Meta:
        managed = False
        db_table = 'analysislevels'


class Associatedsequences(models.Model):
    associatedsequence_id = models.AutoField(db_column='associatedSequence_id', primary_key=True)  # Field name made lowercase.
    gi = models.TextField(db_collation='latin1_swedish_ci')
    shortname = models.CharField(max_length=50, db_collation='latin1_swedish_ci')
    sequence = models.TextField(db_collation='latin1_swedish_ci')
    active = models.IntegerField()
    comments = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    multi_gi = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    sp = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    changelog = models.TextField(db_column='changeLog', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    taxonomy = models.ForeignKey('Taxonomies', models.DO_NOTHING, blank=True, null=True)
    private = models.PositiveIntegerField()
    aliases = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    domaingroup = models.ForeignKey('Domaingroups', models.DO_NOTHING, db_column='domainGroup_id')  # Field name made lowercase.
    proteinlayoutgroup_id = models.IntegerField(db_column='proteinLayoutGroup_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'associatedsequences'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Domainchild(models.Model):
    domaingroupname = models.CharField(db_column='domainGroupName', max_length=50, db_collation='utf8_general_ci')  # Field name made lowercase.
    domaingroup_id = models.IntegerField(db_column='domainGroup_id')  # Field name made lowercase.
    motiflineage = models.CharField(db_column='MotifLineage', max_length=50, db_collation='utf8_general_ci', blank=True, null=True)  # Field name made lowercase.
    domaingroupparent_id = models.CharField(db_column='domainGroupParent_id', max_length=100, db_collation='utf8_general_ci', blank=True, null=True)  # Field name made lowercase.
    analysislevel = models.IntegerField(db_column='analysisLevel')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'domainchild'


class Domaingroups(models.Model):
    domaingroup_id = models.AutoField(db_column='domainGroup_id', primary_key=True)  # Field name made lowercase.
    domaingroupname = models.CharField(db_column='domainGroupName', max_length=50)  # Field name made lowercase.
    domaingroupfunctionalname = models.CharField(db_column='domainGroupFunctionalName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    domaingroupshortname = models.TextField(db_column='domainGroupShortname', blank=True, null=True)  # Field name made lowercase.
    domain = models.ForeignKey('Domains', models.DO_NOTHING)
    domaingroupcomments = models.TextField(db_column='domainGroupComments', blank=True, null=True)  # Field name made lowercase.
    domaingroupparent_id = models.CharField(db_column='domainGroupParent_id', max_length=100, blank=True, null=True)  # Field name made lowercase.
    domaingrouplength = models.IntegerField(db_column='domainGroupLength')  # Field name made lowercase.
    analysislevel = models.IntegerField(db_column='analysisLevel')  # Field name made lowercase.
    appendixname = models.TextField(db_column='appendixName', blank=True, null=True)  # Field name made lowercase.
    mappingstring = models.TextField(db_column='mappingString')  # Field name made lowercase.
    softcutoff = models.FloatField(db_column='softCutoff')  # Field name made lowercase.
    strictcutoff = models.FloatField(db_column='strictCutoff')  # Field name made lowercase.
    domaingroupmodel_id = models.IntegerField(db_column='domainGroupModel_id', blank=True, null=True)  # Field name made lowercase.
    isalignable = models.IntegerField(db_column='isAlignable', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'domaingroups'

    def __str__(self):
        return self.domaingroupname


class Domains(models.Model):
    domain_id = models.AutoField(primary_key=True)
    domainname = models.CharField(db_column='domainName', max_length=50)  # Field name made lowercase.
    domaincomments = models.TextField(db_column='domainComments', blank=True, null=True)  # Field name made lowercase.
    alignment = models.TextField()
    alignmentlength = models.IntegerField(db_column='alignmentLength')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'domains'

    def __str__(self):
        return self.domainname


class Falsepositives(models.Model):
    falsepositive_id = models.AutoField(db_column='falsePositive_id', primary_key=True)  # Field name made lowercase.
    domain_id = models.PositiveIntegerField()
    gi = models.TextField()

    class Meta:
        managed = False
        db_table = 'falsepositives'


class Genes(models.Model):
    gene_id = models.AutoField(primary_key=True)
    ncbigene_id = models.CharField(db_column='ncbiGene_id', max_length=10)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'genes'

    def __str__(self):
        return self.ncbigene_id


class Genomesource(models.Model):
    genomesource_id = models.AutoField(db_column='genomeSource_id', primary_key=True)  # Field name made lowercase.
    taxonomy = models.ForeignKey('Taxonomies', models.DO_NOTHING)
    ftplink = models.TextField(db_column='ftpLink', blank=True, null=True)  # Field name made lowercase.
    wwwlink = models.TextField(db_column='wwwLink', blank=True, null=True)  # Field name made lowercase.
    sequencetype = models.TextField(db_column='sequenceType')  # Field name made lowercase.
    version = models.TextField()
    timecreated = models.DateTimeField(db_column='timeCreated')  # Field name made lowercase.
    timelastmodified = models.DateTimeField(db_column='timeLastModified')  # Field name made lowercase.
    xmlparameter = models.TextField(db_column='xmlParameter')  # Field name made lowercase.
    sourcedatabase = models.TextField(db_column='sourceDatabase')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'genomesource'


class Goldstatus(models.Model):
    goldstamp = models.CharField(db_column='goldStamp', primary_key=True, max_length=10)  # Field name made lowercase.
    ncbi_taxonomy_id = models.IntegerField()
    projectstatus = models.CharField(max_length=25)
    sequencingstatus = models.CharField(max_length=25)

    class Meta:
        managed = False
        db_table = 'goldstatus'


class Inserterrors(models.Model):
    inserterror_id = models.AutoField(db_column='insertError_id', primary_key=True)  # Field name made lowercase.
    motif = models.ForeignKey('Motifs', models.DO_NOTHING)
    startposition = models.IntegerField()
    stopposition = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'inserterrors'


class Layouts(models.Model):
    layout_id = models.AutoField(primary_key=True)
    layoutcomments = models.TextField(db_column='layoutComments', blank=True, null=True)  # Field name made lowercase.
    proteinlayoutgroup = models.ForeignKey('Proteinlayoutgroups', models.DO_NOTHING, db_column='proteinLayoutGroup_id')  # Field name made lowercase.
    sequence = models.OneToOneField('Sequences', models.DO_NOTHING)
    layoutrank = models.IntegerField(db_column='layoutRank')  # Field name made lowercase.
    layoutstatus = models.TextField(db_column='layoutStatus')  # Field name made lowercase.
    layoutstring = models.TextField(db_column='layoutString')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'layouts'


class Methods(models.Model):
    method_id = models.AutoField(primary_key=True)
    domaingroup_id = models.IntegerField(db_column='domainGroup_id')  # Field name made lowercase.
    input = models.TextField(blank=True, null=True)
    type = models.TextField()
    parameter = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'methods'


class Motifs(models.Model):
    sequence = models.ForeignKey('Sequences', models.DO_NOTHING)
    motifname = models.TextField(db_collation='latin1_swedish_ci')
    startposition = models.IntegerField()
    stopposition = models.IntegerField()
    motifcomments = models.TextField(db_column='motifComments', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    domaingroup = models.ForeignKey(Domaingroups, models.DO_NOTHING, db_column='domainGroup_id')  # Field name made lowercase.
    motif_id = models.AutoField(primary_key=True)
    gaps = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    active = models.IntegerField()
    method = models.ForeignKey(Methods, models.DO_NOTHING)
    motifrank = models.IntegerField(db_column='motifRank', blank=True, null=True)  # Field name made lowercase.
    asciioutput = models.TextField(db_column='asciiOutput', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    binaryoutput = models.TextField(db_column='binaryOutput', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'motifs'

    def __str__(self):
        return self.motifname

    def get_evalue(self):
        data_ = {}
        data = ET.fromstring(self.asciioutput)
        for x in data:
            data_[x.tag] = x.text
        return float(data_["eValue"]) if "eValue" in data_ else 0

    def get_ali_positions(self):
        # Returns sequence positions alignment to hmm in 1based coordinates system
        data_ = {}
        data = ET.fromstring(self.asciioutput)
        for x in data:
            data_[x.tag] = x.text
        match = re.search(data_["motif"].strip().replace("-", "").replace("*", "X").upper(), self.sequence.sequence.replace("*", "X").upper())
        return [match.start() + 1, match.end()]

    def get_real_startposition(self):
        # Returns start position of the motif in 1based coordinates system
        return self.get_ali_positions()[0]

    def get_real_stopposition(self):
        # Returns stop position of the motif in 1based coordinates system
        return self.get_ali_positions()[1]

    def get_motif_length(self):
        # Returns length of the motif
        return self.get_real_stopposition() - self.get_real_startposition() + 1


class NcbiTaxonomy(models.Model):
    rank = models.TextField(db_collation='latin1_swedish_ci')
    scientificname = models.TextField(db_column='scientificName', db_collation='latin1_swedish_ci')  # Field name made lowercase.
    division = models.TextField(db_collation='latin1_swedish_ci')
    commonname = models.TextField(db_column='commonName', db_collation='latin1_swedish_ci')  # Field name made lowercase.
    genus = models.TextField(db_collation='latin1_swedish_ci')
    species = models.TextField(db_collation='latin1_swedish_ci')
    subspecies = models.TextField(db_collation='latin1_swedish_ci')
    ncbi_taxonomy_id = models.IntegerField(db_column='ncbi_Taxonomy_id', primary_key=True)  # Field name made lowercase.
    nucnumber = models.IntegerField(db_column='nucNumber', blank=True, null=True)  # Field name made lowercase.
    estnumber = models.IntegerField(db_column='estNumber', blank=True, null=True)  # Field name made lowercase.
    protnumber = models.IntegerField(db_column='protNumber')  # Field name made lowercase.
    structnumber = models.IntegerField(db_column='structNumber', blank=True, null=True)  # Field name made lowercase.
    genomenumber = models.IntegerField(db_column='genomeNumber', blank=True, null=True)  # Field name made lowercase.
    genenumber = models.IntegerField(db_column='geneNumber', blank=True, null=True)  # Field name made lowercase.
    active = models.IntegerField()
    lastupdate = models.DateField(db_column='lastUpdate', blank=True, null=True)  # Field name made lowercase.
    class_field = models.TextField(db_column='class', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field renamed because it was a Python reserved word.
    parent_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'ncbi_taxonomy'


class NcbiTaxonomysynonyms(models.Model):
    name = models.TextField()
    ncbi_taxonomysynonyms_id = models.AutoField(db_column='NCBI_TaxonomySynonyms_id', primary_key=True)  # Field name made lowercase.
    ncbi_taxonomy = models.ForeignKey(NcbiTaxonomy, models.DO_NOTHING, db_column='NCBI_Taxonomy_id')  # Field name made lowercase.
    class_field = models.TextField(db_column='class', blank=True, null=True)  # Field renamed because it was a Python reserved word.

    class Meta:
        managed = False
        db_table = 'ncbi_taxonomysynonyms'


class P2Dmapping(models.Model):
    p2dmapping_id = models.AutoField(db_column='p2dMapping_id', primary_key=True)  # Field name made lowercase.
    domaingroup = models.ForeignKey(Domaingroups, models.DO_NOTHING, db_column='domainGroup_id')  # Field name made lowercase.
    proteinlayoutgroup = models.ForeignKey('Proteinlayoutgroups', models.DO_NOTHING, db_column='proteinLayoutGroup_id')  # Field name made lowercase.
    position = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'p2dmapping'
        unique_together = (('proteinlayoutgroup', 'position'),)


class Proteinlayoutgroups(models.Model):
    proteinlayoutgroup_id = models.AutoField(db_column='proteinLayoutGroup_id', primary_key=True)  # Field name made lowercase.
    proteinlayoutgroupname = models.CharField(db_column='proteinLayoutGroupName', max_length=50)  # Field name made lowercase.
    proteinlayoutgroupfunctionalname = models.CharField(db_column='proteinLayoutGroupFunctionalName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    proteinlayoutgroupshortname = models.TextField(db_column='proteinLayoutGroupShortname', blank=True, null=True)  # Field name made lowercase.
    proteinlayout = models.ForeignKey('Proteinlayouts', models.DO_NOTHING, db_column='proteinLayout_id')  # Field name made lowercase.
    proteinlayoutgroupcomments = models.TextField(db_column='proteinLayoutGroupComments', blank=True, null=True)  # Field name made lowercase.
    proteinlayoutgroupparent_id = models.IntegerField(db_column='proteinLayoutGroupParent_id', blank=True, null=True)  # Field name made lowercase.
    proteinlayoutgrouplength = models.IntegerField(db_column='proteinLayoutGroupLength')  # Field name made lowercase.
    analysislevel = models.IntegerField(db_column='analysisLevel')  # Field name made lowercase.
    appendixname = models.TextField(db_column='appendixName', blank=True, null=True)  # Field name made lowercase.
    mappingstring = models.TextField(db_column='mappingString')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'proteinlayoutgroups'

    def __str__(self):
        return self.proteinlayoutgroupname


class Proteinlayouts(models.Model):
    proteinlayout_id = models.AutoField(db_column='proteinLayout_id', primary_key=True)  # Field name made lowercase.
    proteinlayoutname = models.CharField(db_column='proteinLayoutName', max_length=50)  # Field name made lowercase.
    proteinlayoutcomments = models.TextField(db_column='proteinLayoutComments', blank=True, null=True)  # Field name made lowercase.
    layout = models.TextField()
    layoutlength = models.IntegerField(db_column='layoutLength')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'proteinlayouts'

    def __str__(self):
        return self.proteinlayoutname


class Secondarydomainstructures(models.Model):
    secondarydomainstructure_id = models.AutoField(db_column='secondaryDomainStructure_id', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    dssp = models.TextField()
    domaingroup_id = models.IntegerField(db_column='domainGroup_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'secondarydomainstructures'


class Secondaryproteinlayouts(models.Model):
    secondaryproteinlayout_id = models.AutoField(db_column='secondaryProteinLayout_id', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    dssp = models.TextField()
    proteinlayoutgroup_id = models.IntegerField(db_column='proteinLayoutGroup_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'secondaryproteinlayouts'


class Sequences(models.Model):
    sequence_id = models.AutoField(primary_key=True)
    foreignannotation = models.TextField(db_column='foreignAnnotation', db_collation='latin1_swedish_ci')  # Field name made lowercase.
    sequenceshortname = models.CharField(db_column='sequenceShortname', max_length=50, db_collation='latin1_swedish_ci')  # Field name made lowercase.
    annotation = models.TextField(db_collation='latin1_swedish_ci')
    sequence = models.TextField(db_collation='latin1_swedish_ci')
    sequencestatus = models.TextField(db_column='sequenceStatus', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    sequencecomments = models.TextField(db_column='sequenceComments', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    dbxref = models.CharField(max_length=25, blank=True, null=True)
    changelog = models.TextField(db_column='changeLog', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    taxonomy = models.ForeignKey('Taxonomies', models.DO_NOTHING, blank=True, null=True)
    private = models.PositiveIntegerField()
    aliases = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    sourcedatabase = models.TextField(db_column='sourceDatabase', db_collation='latin1_swedish_ci')  # Field name made lowercase.
    replacedby = models.IntegerField(db_column='replacedBy')  # Field name made lowercase.
    sequencetype = models.CharField(db_column='sequenceType', max_length=25, db_collation='latin1_swedish_ci')  # Field name made lowercase.
    gene = models.ForeignKey(Genes, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'sequences'
        unique_together = (('dbxref', 'sourcedatabase'),)

    def __str__(self):
        return self.sequenceshortname

    @admin.display(
        ordering='sequenceshortname',
        description='Taxa'
    )

    def get_fullTaxa(self, taxonomy_id=-1000, rank=True):
        if taxonomy_id == 1:
            name = "root"
        else:
            taxonomy_id = taxonomy_id if taxonomy_id != -1000 else self.taxonomy.taxonomy_id
            selfTaxa = Taxonomies.objects.get(taxonomy_id=taxonomy_id)
            parent_name = self.get_fullTaxa(selfTaxa.taxonomyparent_id, rank)
            if rank:
                name = " | ".join([ parent_name, ":".join([selfTaxa.taxonomyrank, selfTaxa.scientificname]) ])
            else:
                name = " | ".join([ parent_name, selfTaxa.scientificname ])

        return name

    def get_TaxInfo(self):
        taxas = ["superkingdom", "clade", "kingdom", "phylum", "order", "family", "genus"]
        fullTaxa = {k.split(":")[0]:k.split(":")[1] for k in  [x.strip() for x in self.get_fullTaxa().split("|")] if ":" in k and k.split(":")[0] in taxas}
        return fullTaxa


class Species(models.Model):
    species_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    parent_id = models.IntegerField(blank=True, null=True)
    taxonomy_id = models.PositiveIntegerField()
    shortname = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'species'


class Synonymgroups(models.Model):
    id1 = models.IntegerField()
    id2 = models.IntegerField()
    comments = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'synonymgroups'


class Taxonomies(models.Model):
    taxonomy_id = models.AutoField(primary_key=True)
    commonname = models.TextField(db_column='commonName', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    scientificname = models.TextField(db_column='scientificName', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    taxonomycomments = models.TextField(db_column='taxonomyComments', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    taxonomyparent_id = models.IntegerField(db_column='taxonomyParent_id')  # Field name made lowercase.
    analysislevel = models.CharField(db_column='analysisLevel', max_length=15, db_collation='latin1_swedish_ci')  # Field name made lowercase.
    taxonomyrank = models.TextField(db_column='taxonomyRank', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    taxonomyshortname = models.TextField(db_column='taxonomyShortname', db_collation='latin1_swedish_ci')  # Field name made lowercase.
    ncbi_taxonomy_id = models.IntegerField(db_column='ncbi_Taxonomy_id')  # Field name made lowercase.
    taxonomystatus = models.TextField(db_column='taxonomyStatus', db_collation='latin1_swedish_ci')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'taxonomies'

    def __str__(self):
        return self.scientificname

    def get_fullTaxa(self, rank=True):
        if self.taxonomy_id == 1:
            return "root"
        else:
            parent_taxonomy = Taxonomies.objects.get(taxonomy_id=self.taxonomyparent_id)
            parent_name = parent_taxonomy.get_fullTaxa(rank)
            return " | ".join([parent_name, ":".join([self.taxonomyrank, self.scientificname])]) if rank else " | ".join([parent_name, self.scientificname])


class Tertiarydomainstructures(models.Model):
    tertiarydomainstructure_id = models.AutoField(db_column='tertiaryDomainStructure_id', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50)
    comments = models.TextField()
    pdb = models.TextField()
    domaingroup_id = models.IntegerField(db_column='domainGroup_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tertiarydomainstructures'


class Tertiaryproteinlayouts(models.Model):
    tertiaryproteinlayout_id = models.AutoField(db_column='tertiaryProteinLayout_id', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    pdb = models.TextField()
    proteinlayoutgroup_id = models.IntegerField(db_column='proteinLayoutGroup_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tertiaryproteinlayouts'


class Updatetask2Sequences(models.Model):
    updatetask2sequences_id = models.AutoField(db_column='updateTask2sequences_id', primary_key=True)  # Field name made lowercase.
    sequence = models.ForeignKey(Sequences, models.DO_NOTHING, related_name='Updatetask2Sequences')
    new_sequence = models.ForeignKey(Sequences, models.DO_NOTHING, related_name='new_sequence')
    update_task = models.ForeignKey('Updatetasks', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'updatetask2sequences'


class Updatetask2User(models.Model):
    updatetask2user_id = models.AutoField(primary_key=True)
    updatetask = models.ForeignKey('Updatetasks', models.DO_NOTHING)
    user = models.ForeignKey('User', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'updatetask2user'


class Updatetasks(models.Model):
    updatetask_id = models.AutoField(db_column='updateTask_id', primary_key=True)  # Field name made lowercase.
    updatetasktype = models.CharField(db_column='updateTaskType', max_length=25)  # Field name made lowercase.
    affectedtable = models.CharField(db_column='affectedTable', max_length=25)  # Field name made lowercase.
    updatetaskcomments = models.BigIntegerField(db_column='updateTaskComments', blank=True, null=True)  # Field name made lowercase.
    taskupdatetime = models.DateTimeField(db_column='taskUpdateTime')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'updatetasks'


class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=60)
    password = models.CharField(max_length=60)
    rights = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'user'

    def __str__(self):
        return self.username


class Verifylayouts(models.Model):
    verifylayout_id = models.AutoField(db_column='verifyLayout_id', primary_key=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'verifylayouts'


class Verifymotifs(models.Model):
    sequence = models.ForeignKey(Sequences, models.DO_NOTHING)
    motifname = models.TextField(db_collation='latin1_swedish_ci')
    startposition = models.IntegerField()
    stopposition = models.IntegerField()
    verifymotifcomments = models.TextField(db_column='verifyMotifComments', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    domaingroup = models.ForeignKey(Domaingroups, models.DO_NOTHING, db_column='domainGroup_id')  # Field name made lowercase.
    verifymotif_id = models.AutoField(db_column='verifyMotif_id', primary_key=True)  # Field name made lowercase.
    gaps = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
    active = models.IntegerField()
    method = models.ForeignKey(Methods, models.DO_NOTHING)
    verifymotifrank = models.IntegerField(db_column='verifyMotifRank', blank=True, null=True)  # Field name made lowercase.
    asciioutput = models.TextField(db_column='asciiOutput', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
    binaryoutput = models.TextField(db_column='binaryOutput', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'verifymotifs'

    def __str__(self):
        return self.motifname

    def get_ali_positions(self):
        # Returns sequence positions alignment to hmm in 1based coordinates system
        data_ = {}
        data = ET.fromstring(self.asciioutput)
        for x in data:
            data_[x.tag] = x.text
        match = re.search(data_["motif"].strip().replace("-","").upper(), self.sequence.sequence)
        return [match.start()+1, match.end()]

    def get_real_startposition(self):
        # Returns start position of the motif in 1based coordinates system
        return self.get_ali_positions()[0]

    def get_real_stopposition(self):
        # Returns stop position of the motif in 1based coordinates system
        return self.get_ali_positions()[1]

    def get_motif_length(self):
        # Returns length of the motif
        return self.get_real_stopposition() - self.get_real_startposition() + 1