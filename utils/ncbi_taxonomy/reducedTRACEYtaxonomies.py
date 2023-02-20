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
