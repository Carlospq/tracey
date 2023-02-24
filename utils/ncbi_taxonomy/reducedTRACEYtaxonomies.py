#from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import reducedTRACEYtaxonomies
reducedTRACEYtaxonomies = { 'SAR': {
                                    'Heterokonts': {
                                                    'Bigyra': {},
                                                    'Oomycota': {},
                                                    'Ochrophyta': {},
                                                    'Pelagophyceae': {}
                                    },
                                    'Apicomplexa': {},
                                    'Perkinsozoa': {},
                                    'Dinoflagellates': {},
                                    'Ciliates': {},
                                    'Rhizaria': {}
                            },
                            'Haptophyta': {},
                            'Cryptophyceae': {},
                            'Excavata': {
                                         'Kinetoplastida': {},
                                         'Heterolobosea': {},
                                         'Jakobea': {},
                                         'Metamonada': {}
                            },
                            'Archaeplastida': {
                                               'Glaucophyta': {},
                                               'Rhodophyta': {},
                                               'Viridiplantae': {
                                                                 'Chlorophyta':{
                                                                                'Chlamydomonades': {},
                                                                                'Chlorellales': {},
                                                                                'Sphaeropleales': {},
                                                                                'Mamiellophyceae': {}
                                                                 },
                                                                 'Streptophyta': {
                                                                                  'Klebsormidiophyceae': {},
                                                                                  'Lycopodiopsida': {},
                                                                                  'Polypodiopsida': {},
                                                                                  'Spermatophyta': {
                                                                                                    'Acrogymnospermae': {},
                                                                                                    'Liliopsida': {},
                                                                                                    'Eudicotyledons': {}
                                                                                  }
                                                                 }
                                               }
                            },
                            'Amoebozoa': {
                                          'Discosea': {},
                                          'Archamoeba': {},
                                          'Variosea': {},
                                          'Dictyostelia': {}
                            },
                            'Apusozoa': {},
                            'Opisthokonta': {
                                             'Fungi': {
                                                   'Microsporidia': {},
                                                   'Basal Fungi': {
                                                                   'Cryptomycota': {}
                                                   },
                                                   'Dikarya': {
                                                               'Basidiomycota': {},
                                                               'Ascomycota': {}
                                                   }
                                             },
                                             'Holozoa': {
                                                         'Unicellular Holozoa': {}
                                             },
                                             'Metazoa': {
                                                         'Porifera': {},
                                                         'Ctenophora': {},
                                                         'Cnidaria': {},
                                                         'Placozoa': {},
                                                         'Bilateria': {
                                                                       'Urochordata': {},
                                                                       'Hemichordata': {},
                                                                       'Echinodermata': {},
                                                                       'Vertebrata': {
                                                                                      'Chondrichthyes': {},
                                                                                      'Actinopterygii': {},
                                                                                      'Sarcopterygii': {},
                                                                                      'Tetrapoda':{
                                                                                                   'Amphibia': {},
                                                                                                   'Reptilia': {},
                                                                                                   'Aves': {},
                                                                                                   'Mammalia': {}
                                                                                      },
                                                                       },
                                                                       'Insecta': {},
                                                                       'Crustacea': {},
                                                                       'Chelicerata': {},
                                                                       'Myriapoda': {},
                                                                       'Tardigrada': {},
                                                                       'Nematoda': {},
                                                                       'Mollusca': {},
                                                                       'Brachiopoda': {},
                                                                       'Annelida': {},
                                                                       'Platyhelminthes': {}
                                                         },
                                             }
                            },
                            'Archaea': {
                                        'Asgard group': {},
                                        'DPANN group': {},
                                        'TACK group': {
                                                       'Thaumarchaeota': {},
                                                       'Crenarchaeota': {},
                                                       'Euryarchaeota': {}
                                        }
                            },
                            'Bacteria': {
                                         'Proteobacteria': {
                                                            'Alphaproteobacteria': {},
                                                            'Betaproteobacteria': {},
                                                            'Gammaproteobacteria': {}
                                         },
                                         'Firmicutes': {},
                                         'Cyanobacteria': {},
                                         'Actinobacteria': {},
                                         'FCB group': {},
                                         'PVC group': {},
                                         'Spirochaetes': {},
                                         'Acidobacteria': {}
                            },
                            'Viruses': {
                                        'Megaviricetes': {
                                                          'Mimiviridae': {},
                                                          'Iridoviridae': {},
                                                          'Marseilleviridae': {},
                                                          'Phycodnaviridae': {}
                                        }
                            }
}

def _finditem(obj, key):
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = _finditem(v, key)
            if item is not None:
                return item

def _findKeys(obj, keyList = []):
    for k in obj:
        keyList.append(k)
        if obj[k]:
            _findKeys(obj[k], keyList = keyList)
    return keyList

reducedTRACEYtaxonomiesIDs = {'SAR': 18543, 'Heterokonts': 57, 'Bigyra': 20750, 'Oomycota': 9444, 'Ochrophyta': 23274, 'Pelagophyceae': 9445, 'Apicomplexa': 38, 'Perkinsozoa': 24839, 'Dinoflagellates': 13415, 'Ciliates': 13414, 'Rhizaria': 13405, 'Haptophyta': 13412, 'Cryptophyceae': 13413, 'Excavata': [18551, 18549], 'Kinetoplastida': 50, 'Heterolobosea': 55, 'Jakobea': 13408, 'Metamonada': 18549, 'Archaeplastida': [18237, 40, 18], 'Glaucophyta': 18237, 'Rhodophyta': 40, 'Viridiplantae': 18, 'Chlorophyta': 33, 'Chlamydomonades': 4735, 'Chlorellales': 4752, 'Sphaeropleales': 19880, 'Mamiellophyceae': 20917, 'Streptophyta': 4738, 'Klebsormidiophyceae': 26471, 'Lycopodiopsida': 19740, 'Polypodiopsida': 4743, 'Spermatophyta': 4734, 'Acrogymnospermae': 19749, 'Liliopsida': 4747, 'Eudicotyledons': 4737, 'Amoebozoa': 13406, 'Discosea': 19817, 'Archamoeba': 18545, 'Variosea': None, 'Dictyostelia': 18705, 'Apusozoa': 13417, 'Opisthokonta': 18519, 'Fungi': 13, 'Microsporidia': 21, 'Basal Fungi': 26214, 'Cryptomycota': 26214, 'Dikarya': 18524, 'Basidiomycota': 14, 'Ascomycota': 23, 'Holozoa': [19595, 61, 54], 'Unicellular Holozoa': [19595, 61, 54], 'Metazoa': 6, 'Porifera': 56, 'Ctenophora': 13411, 'Cnidaria': 8, 'Placozoa': 71, 'Bilateria': 70, 'Urochordata': 34, 'Hemichordata': 18219, 'Echinodermata': 25, 'Vertebrata': 15, 'Chondrichthyes': 18223, 'Actinopterygii': 18224, 'Sarcopterygii': 19464, 'Tetrapoda': 18226, 'Amphibia': 16, 'Reptilia': 18229, 'Aves': 36, 'Mammalia': 27, 'Insecta': 10, 'Crustacea': 32, 'Chelicerata': 51, 'Myriapoda': 22533, 'Tardigrada': 48, 'Nematoda': 17, 'Mollusca': 22, 'Brachiopoda': 18547, 'Annelida': 45, 'Platyhelminthes': 35, 'Archaea': 4, 'Asgard group': 24868, 'DPANN group': 22092, 'TACK group': 22028, 'Thaumarchaeota': 5358, 'Crenarchaeota': 5259, 'Euryarchaeota': 5258, 'Bacteria': 11, 'Proteobacteria': 3648, 'Alphaproteobacteria': 3649, 'Betaproteobacteria': 3891, 'Gammaproteobacteria': 3735, 'Firmicutes': 24271, 'Cyanobacteria': 3637, 'Actinobacteria': 4125, 'FCB group': 19987, 'PVC group': 19010, 'Spirochaetes': 21207, 'Acidobacteria': 4241, 'Viruses': 26555, 'Megaviricetes': 18839, 'Mimiviridae': 18841, 'Iridoviridae': 20929, 'Marseilleviridae': 20866, 'Phycodnaviridae': 18965}

reducedTRACEYtaxonomies_ncbiIDs = {'SAR': [5794, 2497438, 2864, 5878, 4762, 5749, 2683628, 2836, 35675, 38410, 569578, 5747, 91989, 136419, 2662056, 2604748], 'Heterokonts': [4762, 5749, 2683628, 2836, 35675, 38410, 569578, 5747, 91989], 'Bigyra': [2683628], 'Oomycota': [4762], 'Ochrophyta': [2836, 35675, 38410, 569578, 5747, 91989], 'Pelagophyceae': [35675], 'Apicomplexa': [5794], 'Perkinsozoa': [2497438], 'Dinoflagellates': [2864], 'Ciliates': [5878], 'Rhizaria': [136419, 2662056, 2604748], 'Haptophyta': [2830], 'Cryptophyceae': [3027], 'Excavata': [5752, 33682, 556282, 5719, 207245, 2662611], 'Kinetoplastida': [5653], 'Heterolobosea': [5752], 'Jakobea': [556282], 'Metamonada': [5719, 207245, 2662611], 'Archaeplastida': [38254, 2763, 33090], 'Glaucophyta': [38254], 'Rhodophyta': [2763], 'Viridiplantae': [33090], 'Chlorophyta': [3041], 'Chlamydomonades': [3042], 'Chlorellales': [35460], 'Sphaeropleales': [35491], 'Mamiellophyceae': [1035538], 'Streptophyta': [35493], 'Klebsormidiophyceae': [131220], 'Lycopodiopsida': [1521260], 'Polypodiopsida': [241806], 'Spermatophyta': [3398, 58019, 3296, 3372, 29811], 'Acrogymnospermae': [58019, 3296, 3372, 29811], 'Liliopsida': [1437197, 16360], 'Eudicotyledons': [3524, 4069, 4143, 4055, 4209, 4036, 41945, 32224, 3646, 72025, 3744, 71239, 3502, 91834, 3699, 41938, 41937, 41944, 41943], 'Amoebozoa': [2605435, 555369, 555280], 'Discosea': [555280], 'Archamoeba': [2682482], 'Variosea': [None], 'Dictyostelia': [2058949, 2058181], 'Apusozoa': [2925400], 'Opisthokonta': [33208, 4751, 28009, 127916, 2687318, 2686024], 'Fungi': [4751], 'Microsporidia': [6029], 'Basal Fungi': [1031332], 'Cryptomycota': [1031332], 'Dikarya': [451864], 'Basidiomycota': [5204], 'Ascomycota': [4890], 'Holozoa': [2687318, 127916, 28009], 'Unicellular Holozoa': [2687318, 127916, 28009], 'Metazoa': [33208], 'Porifera': [6040], 'Ctenophora': [10197], 'Cnidaria': [6073], 'Placozoa': [10226], 'Bilateria': [7586, 7711, 10219, 6231, 42241, 6656, 27563, 33310, 1215728, 6447, 6157, 6340, 7568, 10215, 10205, 10229, 10190, 1312402], 'Urochordata': [7712], 'Hemichordata': [10219], 'Echinodermata': [7586], 'Vertebrata': [7777, 7898, 8287, 117565, 117569], 'Chondrichthyes': [7777], 'Actinopterygii': [7898], 'Sarcopterygii': [7894], 'Tetrapoda': [8292, 40674, 8504, 8782, 1294634, 2841271], 'Amphibia': [8292], 'Reptilia': [8504], 'Aves': [8782], 'Mammalia': [40674], 'Insecta': [50557], 'Crustacea': [6657], 'Chelicerata': [6843], 'Myriapoda': [61985], 'Tardigrada': [42241], 'Nematoda': [6231], 'Mollusca': [6447], 'Brachiopoda': [7568], 'Annelida': [6340], 'Platyhelminthes': [6157], 'Archaea': [2157], 'Asgard group': [1655434], 'DPANN group': [192989, 1462422, 1801631], 'TACK group': [28889, 651137, 51967, 928852], 'Thaumarchaeota': [651137], 'Crenarchaeota': [28889], 'Euryarchaeota': [28890], 'Bacteria': [2], 'Proteobacteria': [1224], 'Alphaproteobacteria': [28211], 'Betaproteobacteria': [28216], 'Gammaproteobacteria': [1236], 'Firmicutes': [84086], 'Cyanobacteria': [1117], 'Actinobacteria': [85003], 'FCB group': [65842, 142182, 1379697, 62680, 456828, 976, 1134404, 1090, 1936987, 74015, 142187], 'PVC group': [74201, 256845, 203682, 204428, 67812], 'Spirochaetes': [203691], 'Acidobacteria': [57723], 'Viruses': [10239], 'Megaviricetes': [2732523], 'Mimiviridae': [549779], 'Iridoviridae': [10486], 'Marseilleviridae': [944644], 'Phycodnaviridae': [10501]}

# def getNonClades(ncbiID, l=[]):
#     t = Taxonomies.objects.get(ncbi_taxonomy_id=ncbiID)
#     children = Taxonomies.objects.filter(taxonomyparent_id=t.taxonomy_id)
#     for c in children:
#         if c.taxonomyrank == 'clade':
#             getNonClades(c.ncbi_taxonomy_id, l=l)
#         else:
#             l.append(c.ncbi_taxonomy_id)
#     print(l)

# for name in reducedTRACEYtaxonomies_ncbiIDs:
#     for id_ in reducedTRACEYtaxonomies_ncbiIDs[name]:
#         if id_ == None: continue
#         t = Taxonomies.objects.get(ncbi_taxonomy_id=id_)
#         if t.taxonomyrank == 'clade':
#             print(t, t.ncbi_taxonomy_id, t.taxonomy_id)
