# Run code when run as script
# python manage.py shell < utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py

#### SCRIPT OPTIMIZED FOR SNARE DOMAINGROUPS

if __name__ == "django.core.management.commands.shell":

	from apps.home.models import *
	from apps.templates.menus.query_sequences import *

	snare_domaingroupNames = menu['SNARE']['SNARE']

	def updateDomainGroups(domaingroups_dict, dgParent=None):

		if not domaingroups_dict: return
		if not dgParent:
			dgParent = Domaingroups.objects.get(domaingroupname="SNARE")
		snare_domain = Domains.objects.get(domainname='SNARE')

		# Add new domaingroups matching new SNARE HMMs
		for dgKeyName in domaingroups_dict:

			# Check if dgKeyName exists - Create new dg if not
			if not Domaingroups.objects.filter(domaingroupname=dgKeyName):

				with open('utils/hmmModels/SNARE/%s' % (dgKeyName + ".hmm"), 'r') as hmm_file:
					dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])

				dg = Domaingroups(domaingroupname=dgKeyName,
								  domaingrouplength=dgLen,
								  domain=snare_domain,
								  domaingroupparent_id=dgParent.domaingroup_id,
								  analysislevel=5,
								  softcutoff=1.0,
								  strictcutoff=1.0)
				dg.save()

			if domaingroups_dict[dgKeyName]:
				updateDomainGroups(domaingroups_dict[dgKeyName], Domaingroups.objects.get(domaingroupname=dgKeyName))

	updateDomainGroups(snare_domaingroupNames)