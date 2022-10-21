# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import re
from django import forms
from django.core import validators
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from time import gmtime, strftime

from django.utils.translation import gettext_lazy as _

from django.db import models
from django.forms import ModelForm

from .models import *


def NCBIpattern(value):
    pattern = re.compile("^gi\|([0-9]+)$")
    if not pattern.match(value):
        raise forms.ValidationError('Foreign annotation format is not correct. Please use NCBI format.')
    return value


class MultipleChoiceFieldNoValidation(forms.MultipleChoiceField):
    def validate(self, value):
        pass


class FamilyForm(forms.Form):

    class Meta:
        help_texts = {
            'taxonomy': ''
        }

    # Motif
    domainname = forms.CharField(
                    label= "Motif Name",
                    required = False,
                    initial = "SNARE",
                    widget = forms.Select(choices = [ (x.domainname, x.domainname) for x in Domains.objects.all() ])
                )
    domainname.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    # Shortname
    shortname = forms.CharField(
                    label= "shortname",
                    required = False,
                    widget = forms.Select()
                )

    # Taxonomy
    taxonomy_rank = forms.CharField(
                    label= "taxonomy_rank",
                    required = False,
                    widget = forms.Select()
                )
    taxonomy = MultipleChoiceFieldNoValidation(
                    initial=123,
                    label= "taxonomy",
                    required = False,
                )
    taxonomy.widget.attrs.update({'size': 7,
                                  'style': 'width: 100%; margin-top: 6px'})

    # Foreign annotation
    foreignannotation = forms.CharField(
                            label = "foreignannotation",
                            required = False,
                            validators = [validators.RegexValidator('^gi\|([0-9]+)$',
                                                         'Foreign annotation format is not correct. Please use NCBI format.')]
                        )
                        # [NCBIpattern]
    foreignannotation.widget.attrs.update({'type': 'text',
                                           'style': 'width: 100%;',
                                           'placeholder': "ex: 'gi|21426793'"})

    # Domain group
    domaingroup_rank = forms.CharField(
                    label= "domaingroup_rank",
                    required = False,
                    widget = forms.Select()
                )
    domaingroup = MultipleChoiceFieldNoValidation(
                        label = "domaingroup",
                        required = False,
                    )
    domaingroup.widget.attrs.update({'size': 7,
                                     'style': 'width: 100%; margin-top: 6px'})


class InsertSequence(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        helptexts = {'foreignannotation': 'NCBI gene ID annotation',
                     'sequenceshortname': '',
                     'annotation': '',
                     'sequence': '',
                     'sequencestatus': '',
                     'sequencecomments': '',
                     'taxonomy': '',
                     'private': '',
                     'aliases': '',
                     'sourcedatabase': '',
                     'gene': '- If blank an empty instance of gene will be assigned to this sequence\n- "not_specified:-1:###" means an empty instance of Gene has been asigned to this sequence',
                     'sequencetype': '',
                     'changelog': '',
                     'newChangelog': 'Short and clear description of the modification',
                     'replacedby': '',
                     'dbxref': ''}

        for f in self.fields:
            self.fields[f].help_text = helptexts[f]

    class Meta:
        model = Sequences
        fields = [# 'sequence_id', # = models.AutoField(primary_key=True)
                  'foreignannotation', # = models.TextField(db_column='foreignAnnotation', db_collation='latin1_swedish_ci')  # Field name made lowercase.
                  'sequenceshortname', # = models.CharField(db_column='sequenceShortname', max_length=50, db_collation='latin1_swedish_ci')  # Field name made lowercase.
                  'annotation', # = models.TextField(db_collation='latin1_swedish_ci')
                  'sequence', # = models.TextField(db_collation='latin1_swedish_ci')
                  'sequencestatus', # = models.TextField(db_column='sequenceStatus', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
                  'sequencecomments', # = models.TextField(db_column='sequenceComments', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
                  'dbxref', # = models.CharField(max_length=25)
                  'changelog', # = models.TextField(db_column='changeLog', db_collation='latin1_swedish_ci', blank=True, null=True)  # Field name made lowercase.
                  'newChangelog',
                  'taxonomy', # = models.ForeignKey('Taxonomies', models.DO_NOTHING, blank=True, null=True)
                  'private', # = models.PositiveIntegerField()
                  'aliases', # = models.TextField(db_collation='latin1_swedish_ci', blank=True, null=True)
                  'sourcedatabase', # = models.TextField(db_column='sourceDatabase', db_collation='latin1_swedish_ci')  # Field name made lowercase.
                  'replacedby', # = models.IntegerField(db_column='replacedBy')  # Field name made lowercase.
                  'sequencetype', # = models.CharField(db_column='sequenceType', max_length=25, db_collation='latin1_swedish_ci')  # Field name made lowercase.
                  'gene', # = models.ForeignKey(Genes, models.DO_NOTHING)
                 ]

    replacedby = forms.IntegerField(required=False, widget=forms.HiddenInput(), )
    dbxref = forms.CharField(required=False, widget=forms.HiddenInput(), )
    ########################################################################################################################
    sequenceshortname = forms.CharField(required=True, label="Sequence shortname")
    sequenceshortname.widget.attrs.update({'rows': 1, 'style': 'width: 100%; resize: none; display:inline-block; vertical-align:middle;'})

    aliases = forms.CharField(required = False, label="Alias")
    aliases.widget.attrs.update({'rows': 1, 'style': 'width: 100%; resize: none;'})

    foreignannotation = forms.CharField(required=False, label="Foreign annotation")
    foreignannotation.widget.attrs.update({'rows': 1, 'placeholder': "ex: 'gi|21426793'", 'style': 'width: 100%; resize: none;'})
    #######################################################################################################################
    sequence = forms.CharField(required=True, label="Sequence", widget=forms.Textarea(attrs={'rows': 5}))
    sequence.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})
    #######################################################################################################################
    taxonomy = forms.ModelChoiceField(required=True, label="Taxonomy", queryset=Taxonomies.objects.filter().order_by('scientificname'), empty_label="")
    taxonomy.widget.attrs.update({'style': 'width: 100%; resize: none;'})

    sourcedatabase = forms.CharField(required=False, label="Source database")
    sourcedatabase.widget.attrs.update({'rows': 1, 'style': 'width: 100%; resize: none;'})

    gene = forms.CharField(required=False, label='NCBI gene ID')
    gene.widget.attrs.update({'style': 'width: 100%; resize: none;'})
    #######################################################################################################################
    annotation = forms.CharField(required=False, label='Annotation', widget=forms.Textarea(attrs={'rows': 5}))
    annotation.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})
    #######################################################################################################################
    sequencetype = forms.ChoiceField(required=True, label='Sequence type', choices=([('protein','Protein'), ('dna','DNA'), ('rna','RNA'), ('unknown','Unknown')]), initial="Protein")
    sequencetype.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})

    sequencestatus = forms.ChoiceField(required=False, label='Sequence status',  initial='',
                                       choices=( [('',''), ('suppressed','suppresed'), ('dead', 'dead'), ('live', 'live'), ('crystal structure', 'crystal structure'), ('replaced NCBI', 'replaced NCBI'), ('ignore', 'ignore'), ('replaced', 'replaced'), ('unknown', 'uknown')] ))
    sequencestatus.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})

    private = forms.ChoiceField(required=False, label='Private', choices=( [(0,"No"), (1,"Yes")] ), initial=1)
    private.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})
    #######################################################################################################################
    sequencecomments = forms.CharField(required=False, label='Sequence comments', widget=forms.Textarea(attrs={'rows': 5}))
    sequencecomments.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})
    #######################################################################################################################
    changelog = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    changelog.widget.attrs.update({'readonly': True, 'style': 'height: 100%; width: 100%; resize: none;'})
    newChangelog = forms.CharField(required=False, label="Changelog", widget=forms.Textarea(attrs={'rows': 1}))
    newChangelog.widget.attrs.update({'style': 'height: 100%; width: 100%; resize: none;'})
    #######################################################################################################################

    def clean_changelog(self):
        data = [ self.cleaned_data['changelog'] if self.cleaned_data['changelog'] else "" ][0]
        newdata = [ self.data.get('newChangelog') if self.data.get('newChangelog') else "" ][0]
        return data + newdata

    def clean_gene(self):
        ncbigene_id = self.cleaned_data['gene']
        if 'create_new' in ncbigene_id:
            ncbigene_id = ncbigene_id.split('create_new:')[1]
            return Genes.objects.create(ncbigene_id=ncbigene_id)
        elif 'not_specified' in ncbigene_id:
            gene_id = ncbigene_id.split(':')[2]
            return Genes.objects.get(gene_id=gene_id)
        else:
            try:
                return Genes.objects.get(ncbigene_id=ncbigene_id)
            except:
                raise ValidationError("NCBI gene ID %s does not exist"%(ncbigene_id))

    def clean_replacedby(self):
        data = self.cleaned_data['replacedby']
        if data == None:
            data = -1
        return data

    def clean_dbxref(self):
        dbxref = self.cleaned_data['dbxref']
        try:
            sourceDB = self.cleaned_data['sourcedatabase']
        except KeyError:
            sourceDB = ""

        if dbxref == None or dbxref=="":
            if sourceDB == None or sourceDB == "":
                try:
                    new_dbxref = str(max([ int(x.dbxref) for x in Sequences.objects.filter(sourcedatabase="") ]) + 1)
                except:
                    new_dbxref = '1'
            else:
                raise ValidationError("dbxref is required")
        else:
            if sourceDB == None or sourceDB == "":
                raise ValidationError("sourceDB is required")
            else:
                if dbxref in set([x.dbxref for x in Sequences.objects.filter(sourcedatabase=sourceDB)]):
                    raise ValidationError("dbxref '%s' already exists in TRACEY for sourcedatabase '%s'"%(dbxref, sourceDB))
                else:
                    new_dbxref = dbxref

        return new_dbxref

    def clean_sourcedatabase(self):
        sourceDB = self.cleaned_data['sourcedatabase']
        if sourceDB == None or sourceDB == "":
            data = ''

        return data


class MotifForm(forms.Form):

    class Meta:
        help_texts = {
            '': ''
        }

    # shortname = forms.CharField(
    #                 label= "shortname",
    #                 required = False,
    #                 widget = forms.Select()
    #             )

    domainname = forms.CharField(
                    label= "Domain Name",
                    required = False,
                    initial = "",
                    widget = forms.Select(choices = [("","")] + sorted([ (x.domainname, x.domainname) for x in Domains.objects.all() ]))
                )
    domainname.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    domaingroup_rank = forms.CharField(
                    label= "Domain group",
                    required = False,
                    widget = forms.Select(choices = [("","")] + sorted([ (x.domaingroupname, x.domaingroupname) for x in Domaingroups.objects.all() if x.analysislevel == 2 ]))
                )
    domaingroup_rank.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    domaingroup = forms.CharField(
                    label= "Domain subgroup",
                    required = False,
                    widget = forms.Select(choices = [("","")] + sorted([ (x.domaingroupname, x.domaingroupname) for x in Domaingroups.objects.all() if x.analysislevel > 2 ]))
                )
    domaingroup.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    taxonomy = forms.CharField(
                    label= "Taxonomy",
                    required = False,
                    widget = forms.Select(choices = [("","")] + sorted([ (t.scientificname, t.scientificname) for t in Taxonomies.objects.all() ]))
                )
    taxonomy.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    status = forms.CharField(
                    label= "Status",
                    required = False,
                    widget = forms.Select(choices = [("",""), ('crystal structure', 'crystal structure'), ('dead', 'dead'), ('ignore', 'ignore'), ('live', 'live'), ('replaced', 'replaced'), ('replaced NCBI', 'replaced NCBI'), ('suppressed', 'suppressed'), ('unknown', 'unknown')] )
                )
    status.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    private = forms.CharField(
                    label= "Status",
                    required = False,
                    widget = forms.Select(choices = [ ("",""), (0,0), (1,1)])
                )
    private.widget.attrs.update({'style': 'width: 100%; margin-top: 6px'})

    def clean_domainname(self):
        data = self.cleaned_data
        domainname = data['domainname']
        taxonomy = self.data.get('taxonomy')
        if (not domainname and not taxonomy) or not data:
            raise ValidationError("At least 'Domain name' or 'Taxonomy' fields are required")
        return domainname

    def clean_domaingrouprank(self):
        return self.cleaned_data['domaingrouprank']

    def clean_domainsubgroup(self):
        return self.cleaned_data['domainsubgroup']

    def clean_taxonomy(self):
        data = self.cleaned_data
        domainname = self.data.get('domainname')
        taxonomy = data['taxonomy']
        if (not domainname and not taxonomy) or not data:
            raise ValidationError("At least 'Domain name' or 'Taxonomy' fields are required")
        return taxonomy

    def clean_status(self):
        return self.cleaned_data['status']

    def clean_private(self):
        return self.cleaned_data['private']
