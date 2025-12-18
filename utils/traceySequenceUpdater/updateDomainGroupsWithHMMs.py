# Run code when run as script
# python manage.py shell < utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py

#### SCRIPT OPTIMIZED FOR SNARE DOMAINGROUPS

if __name__ == "django.core.management.commands.shell":

	from apps.home.models import *
	from apps.templates.menus.query_sequences import *

	snare_domaingroupNames = menu['SNARE']['SNARE']
	habc_domaingroupNames = menu['SNARE']['Habc']

	def updateDomainGroups(domaingroups_dict, dgParent=None, domain="SNARE"):

		if not domaingroups_dict: return
		if not dgParent:
			if domain == "SNARE":
				dgParent = Domaingroups.objects.get(domaingroupname="SNARE")
			else:
				dgParent = Domaingroups.objects.get(domaingroupname=domain)

		if domain == "SNARE":
			snare_domain = Domains.objects.get(domainname='SNARE')
		else:
			snare_domain = Domains.objects.get(domainname=domain)

		# Add new domaingroups matching new SNARE HMMs
		for dgKeyName in domaingroups_dict:

			# Check if dgKeyName exists - Create new dg if not
			if not Domaingroups.objects.filter(domaingroupname=dgKeyName):

				folder_name = snare_domain.domainname.upper()
				with open('utils/hmmModels/%s/%s' % (folder_name, dgKeyName + ".hmm"), 'r') as hmm_file:
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
				updateDomainGroups(domaingroups_dict[dgKeyName], Domaingroups.objects.get(domaingroupname=dgKeyName), domain=domain)

	updateDomainGroups(snare_domaingroupNames)
	updateDomainGroups(habc_domaingroupNames, Domaingroups.objects.get(domaingroupname="Habc"), domain="Habc")