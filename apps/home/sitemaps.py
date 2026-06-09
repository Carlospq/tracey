from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return ['home', 'query', 'trees', 'features', 'query-sequences', 'query-motifs']

    def location(self, item):
        return reverse(item)
