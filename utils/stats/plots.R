list.of.packages <- c("ggplot2", "ggnewscale", "ggrepel", "ggalluvial", "patchwork", "dplyr", "tidyr", "ggh4x", "grid", "stringr", "reshape2")
lapply(list.of.packages, require, character.only = TRUE)

#library(ggplot2)
#library(ggnewscale)
#library(ggrepel)
#library(ggalluvial)
#library(patchwork)
#library(dplyr)
#library(tidyr)
#library(ggh4x)
#library(grid)
#library(stringr)
#library(reshape2)

setwd('C:/Users/cpulidoq/Documents/traceyDB/')

#### LOAD DATA
# Colors
#plotColors <- list(Archaea = "#440154FF",
#                   Eubacteria = "#443A83FF",
#                   Eukaryota = "#31688EFF", 
#                   Unknown = "#21908CFF",
#                   Viridiplantae = "#FDE725FF",
#                   Metazoa = "#8FD744FF", 
#                   Fungi = "#35B779FF")

plotColors <- c(Archaea = "#E78AC3",
                Eubacteria = "#8DA0CB",
                Bacteria = "#8DA0CB",
                Eukaryota = "#1B9E77", 
                Viruses = "#D95F02",
                Unknown = "#BEBEBE",
                Viridiplantae = "#66C2A4",
                Metazoa = "#238B45", 
                Fungi = "#00441B",
                Bamfordvirae = "#8C2D04",
                Heunggongvirae = "#D95F02",
                Orthornavirae = "#FB9A29",
                Pararnavirae = "#FEC44F",
                "Active w/ motifs" = "#FFE082",
                "Inactive w/ motifs" = "#F4A6A6",
                "Active w/o motifs" = "#FFE08280",
                "Inactive w/o motifs" = "#F4A6A680")


## DATA
# Load Taxonomy data
taxonomydata <- read.csv('./utils/stats/taxonomyData.tsv', sep='\t', header=TRUE, stringsAsFactors=TRUE) %>% filter(active_sequences > 0)
td <- taxonomydata %>% group_by(superkingdom, kingdom) %>% mutate(sequences = sum(sequences),
                                                                  inactive_sequences = sequences - sum(active_sequences),
                                                                  active_sequences = sum(active_sequences),
                                                                  active_motif = sum(active_motif),
                                                                  active_nomotif = sum(active_nomotif),
                                                                  inactive_motif = sum(inactive_motif),
                                                                  inactive_nomotif = sum(inactive_nomotif),
                                                                  n_phylum = length(unique(phylum)),
                                                                  n_species = length(unique(species))) %>%
                            ungroup() %>% select(-phylum, -species, -sequences) %>% unique() %>%
                            mutate(order = paste0(superkingdom, kingdom)) %>%
                            arrange(match(order, c("VirusesBamfordvirae", "VirusesHeunggongvirae", "VirusesOrthornavirae", "VirusesPararnavirae", "VirusesUnknown",
                                                   "UnknownUnknown",
                                                   "EukaryotaUnknown", "EukaryotaViridiplantae", "EukaryotaMetazoa", "EukaryotaFungi",
                                                   "BacteriaUnknown", "EubacteriaUnknown", "ArchaeaUnkown"
                                                   ))) %>%
                            ungroup() %>% mutate(y = cumsum(n_phylum) - 0.5 * n_phylum,
                                                 kingdomLabel = round(n_phylum/sum(n_phylum)*100)) %>%
                            arrange(match(superkingdom, c("Viruses", "Unknown", "Eukaryota", "Eubacteria", "Archeaea"))) %>%
                            mutate(superkingdomN = cumsum(n_phylum), angle = sum(n_phylum)) %>% group_by(superkingdom) %>%
                            mutate(superkingdomN = mean(superkingdomN - n_phylum/2),
                                   angle = -superkingdomN/angle*360)
td

# Taxonomy long format
sd <- melt(td, id.vars=c("superkingdom", "kingdom", "order", "n_phylum"), measure.vars=c("active_motif", "active_nomotif", "inactive_motif", "inactive_nomotif")) %>%
                            arrange(match(order, c("UnknownUnknown",
                                                   "EukaryotaUnknown", "EukaryotaViridiplantae", "EukaryotaMetazoa", "EukaryotaFungi",
                                                   "BacteriaUnknown", "EubacteriaUnknown", "ArchaeaUnkown",
                                                   "VirusesBamfordvirae", "VirusesHeunggongvirae", "VirusesOrthornavirae", "VirusesPararnavirae", "VirusesUnknown"))) %>%
                            group_by(order) %>% mutate(y = value/sum(value)*n_phylum,
                                                       motif_pattern = ifelse(grepl("nomotif", variable), "nomotif", "motif"),
                                                       variable = case_when(variable == "active_motif" ~ "Active w/ motifs",
                                                                            variable == "active_nomotif" ~ "Active w/o motifs",
                                                                            variable == "inactive_motif" ~ "Inactive w/ motifs",
                                                                            variable == "inactive_nomotif" ~ "Inactive w/o motifs")) %>%
                            arrange(match(superkingdom, c("Archaea", "Bacteria", "Eubacteria", "Eukaryota", "Unknown", "Viruses")))
sd

# Load sequences data
sourcedatabase_data <- read.csv('./utils/stats/sequencesData.tsv', sep='\t', header=TRUE, stringsAsFactors=TRUE)
colnames(sourcedatabase_data) <- c("shortname", "superkingdom", colnames(sourcedatabase_data)[3:length(colnames(sourcedatabase_data))])
sourcedatabase_data$shortname <- as.character(sourcedatabase_data$shortname)
sourcedatabase_data[sourcedatabase_data$shortname == "", ]$shortname <- "Unknown"
levels(sourcedatabase_data$superkingdom)[match("", levels(sourcedatabase_data$superkingdom))] <- "Unknown"
levels(sourcedatabase_data$kingdom     )[match("", levels(sourcedatabase_data$kingdom))] <- "Unknown"
sourcedatabase_data <- sourcedatabase_data %>%
                            mutate(sequence_status = ifelse(sequence_status == "live", "active", "inactive"),
                                   sequence_status = case_when(sequence_status == "active" & motifs > 0 ~ "Active w/ motifs",
                                                               sequence_status == "active" & motifs == 0 ~ "Active w/o motifs",
                                                               sequence_status == "inactive" & motifs > 0 ~ "Inactive w/ motifs",
                                                               sequence_status == "inactive" & motifs == 0 ~ "Inactive w/o motifs")) %>%
                            group_by(superkingdom, kingdom, source_db, sequence_status) %>% 
                            summarise(sequences = n()) %>%
                            mutate(source_db = case_when(sum(sequences) < 1000 ~ "Others",
                                                         TRUE ~ source_db))
sourcedatabase_data

# HMM data
hmmData <- data.frame(hmm = c("AAA.AAA", "AAA.ND", "ARF", "C2", "HABC", "LGL", "MUN.D1", "MUN.D2", "NSR.CD", "NSR.MD", "NSR.ND", "PROPPIN", "RAS", "RHOMBOID", "RINT", "SEC39", "SM.D1", "SM.D2A", "SM.D2B", "SM.D3", "SNAP", "SNARE", "ZW10"),
                      # n = c(45, 13, 25, 38, 22, 1, 6, 6, 3, 5, 3, 8, 75, 30, 1, 1, 8, 8, 6, 6, 3, 82, 1)) %>%  # for all db copy
                      n = c(45, 13, 23, 38, 28, 1, 6, 6, 3, 5, 3, 8, 75, 30, 1, 0, 8, 8, 6, 6, 3, 172, 1)) %>%  # for new db copy
                            mutate(hmm = case_when(hmm == "Snare" ~ "SNARE",
                                                   str_detect(hmm, "AAA") ~ "AAA",
                                                   str_detect(hmm, "MUN") ~ "MUN",
                                                   str_detect(hmm, "SM") ~ "SM",
                                                   str_detect(hmm, "NSR") ~ "NSR",
                                                   TRUE ~ hmm)) %>% group_by(hmm) %>%
                            summarise(n = sum(n)) %>% arrange(match(hmm, rev(hmm))) %>%
                            mutate(label = paste0(hmm, ": ", n),
                                   y = cumsum(n) - 0.5 * n)
hmmData

# Load sequences/motifs data
motifsData <- read.csv('./utils/stats/motifsData.tsv', sep='\t', header=TRUE, stringsAsFactors=TRUE) %>%
                            mutate(motifName = case_when(motifName == "Snare" ~ "SNARE",
                                                         str_detect(motifName, "AAA") ~ "AAA",
                                                         str_detect(motifName, "MUN") ~ "MUN",
                                                         str_detect(motifName, "SM") ~ "SM",
                                                         str_detect(motifName, "NSR") ~ "NSR",
                                                         TRUE ~ motifName))
head(motifsData)


## PLOTS
# Sequences in tracey
p0 <- ggplot(sd, aes(x=superkingdom, y=value, fill=variable)) +
          annotate(geom = "label", x = 1, y = sum(sd$value)*.4, fill = "white", alpha = 0, hjust = 0,
                   label = paste("Total sequences:", sum(sd$value),
                                 "\n    Active:",      sum(sd[grepl("Active", sd$variable), "value"]),
                                 "\n        w/ motifs: ", sum(sd[grepl("Active", sd$variable) & grepl("w/ motifs", sd$variable), "value"]),
                                 "\n        w/o motifs:", sum(sd[grepl("Active", sd$variable) & grepl("w/o motifs", sd$variable), "value"]),
                                 "\n    Inctive:",      sum(sd[grepl("Inactive", sd$variable), "value"]),
                                 "\n        w/ motifs: ", sum(sd[grepl("Inactive", sd$variable) & grepl("w/ motifs", sd$variable), "value"]),
                                 "\n        w/o motifs:", sum(sd[grepl("Inactive", sd$variable) & grepl("w/o motifs", sd$variable), "value"])
                   ),
                   label.padding = unit(1, "lines"),
                   size = 3.5
          ) + 
          coord_cartesian(xlim = c(1, 1.05), ylim = c(NA, NA)) +
          theme_void() +
          labs(title = "Sequences Source and Number") +
          theme(plot.margin = margin(t=0, r=20, b=0, l=0, unit="pt"),
                plot.title = element_text(size=20, face="bold"))
p0


strip_backgrounds <- rectGrob(x=.5, y=c(.5, 1.5, 2.5, 3.5, 4.5), gp=gpar(color='black',
                                                                    fill=c(sapply(unique(sd$superkingdom), function(x) { plotColors[[as.character(x)]] } )),
                                                                    alpha=1))
p1 <- ggplot(sd, aes(x=superkingdom, y=value, fill=variable)) +
          geom_bar(stat = "identity", show.legend = FALSE) +
          scale_fill_manual(name = "Sequences status",
                            values = plotColors) +
          scale_y_continuous(limits = c(0, 210000), 
                             position = "right",
                             expand = expansion(add = c(0.5, 0))) + 
          coord_flip(clip='off') +
          scale_x_discrete(position = "top", expand = expansion(add = c(0.5, 0))) +
          theme_void() +
          theme(axis.text.y = element_text(size=12, color="black", angle = -90, hjust=.5, vjust=1),
                axis.text.x = element_text(size=14, angle=45, hjust=0, vjust=.1),
                plot.margin = margin(t=0, r=20, b=0, l=0, unit="pt"),
                panel.grid.major.x = element_line(color="grey"),
                
                plot.title = element_text(size=20, face="bold")) +
          annotation_custom(
            grob=strip_backgrounds, xmin = .5, xmax = 1.5, ymin = 208000, ymax=230000
          )
p1



# Taxonomy Piechart
p2 <- ggplot(td) +
          # Superkingdom column 
          geom_bar(mapping = aes(x=2, y=n_phylum, fill=superkingdom, group=superkingdom), stat = "identity", linewidth=.2, color="white") +
          scale_fill_manual(name = "Superkingdom",
                            values = plotColors) +
                              #c("Archaea" = plotColors[["Archaea"]],
                              #         "Eubacteria" = plotColors[["Eubacteria"]],
                              #         "Eukaryota" = plotColors[["Eukaryota"]], 
                              #         "Unknown" = plotColors[["Unknown"]])) +
          new_scale_fill() +
          
          # Kingdom column
          geom_bar(mapping = aes(x=.7, y=n_phylum, fill=kingdom, group=superkingdom), stat = "identity", linewidth=.2, color="white") +
          scale_fill_manual(name = "Kingdom",
                            values = plotColors) +
                            #c("Viridiplantae" = plotColors[["Viridiplantae"]],
                            #           "Metazoa" = plotColors[["Metazoa"]], 
                            #           "Fungi" = plotColors[["Fungi"]], 
                            #           "Unknown" = plotColors[["Unknown"]])) +
          new_scale_fill() +
          
          # Active/ Inactive sequences column
          geom_bar(data = sd,
                   mapping = aes(x = 2.6, y=y, fill = variable, group = superkingdom),
                   stat = "identity", linewidth=.5, width=.2, color="white") +
          scale_fill_manual(name = "Sequences status",
                            values = c("Active w/ motifs" = plotColors[["Active w/ motifs"]],
                                       "Active w/o motifs" = plotColors[["Active w/o motifs"]],
                                       "Inactive w/ motifs" = plotColors[["Inactive w/ motifs"]],
                                       "Inactive w/o motifs" = plotColors[["Inactive w/o motifs"]])) + 
          
          # LABELS & %
          geom_label(mapping = aes(x=2, y=superkingdomN, label=superkingdom, angle=angle)) +
          geom_label(mapping = aes(x=.7, y=y, label=paste0(kingdomLabel, "%")), show.legend = FALSE) +
          
          # THEME & SCALES
          xlim(-1,3) +
          coord_polar(theta = "y") +
          labs(title = "Taxonomies representation in TRACEY") +
          theme_void() +
          theme(legend.text = element_text(size=14),
                legend.title = element_text(size=16),
                plot.title = element_text(size=20, face="bold", hjust = .5),
                plot.margin = margin(t=0, r=0, b=0, l=0, unit="pt"))
p2



# Sourdatabases barplots
strip_backgrounds <- c(lapply(unique(sourcedatabase_data$superkingdom), function(x) { element_rect(fill = plotColors[[as.character(x)]]) }))
p3 <- ggplot(sourcedatabase_data, aes(x = source_db, y = sequences, fill = sequence_status)) +
          geom_bar(stat = "identity", show.legend = FALSE) +
          scale_fill_manual(name = "Sequences status",
                            values = c("Active w/ motifs" = plotColors[["Active w/ motifs"]],
                                       "Active w/o motifs" = plotColors[["Active w/o motifs"]],
                                       "Inactive w/ motifs" = plotColors[["Inactive w/ motifs"]],
                                       "Inactive w/o motifs" = plotColors[["Inactive w/o motifs"]])) +
          facet_grid2(superkingdom ~ ., scales = "free_y", 
                     strip = strip_themed(background_y = strip_backgrounds)) + 
          scale_x_discrete(position = "top", expand = expansion(add = c(0.5, 0))) +
          theme_void() + 
          theme(axis.text.y = element_text(color="black"),
                axis.text.x = element_text(size=14, angle=45, hjust=0, vjust=.1),
                strip.text.y.right = element_text(angle = -90, size=14),
                panel.grid.major.y = element_line(color="grey"),
                plot.title = element_text(size=20, face="bold"))
p3



# Boxplot sequences per species
text_labels <- taxonomydata %>%
          group_by(superkingdom, kingdom) %>%
          summarise(total_sequences = sum(sequences),
                    nspecies = n(),
                    y = max(sequences)) %>%
          mutate(label = paste0("Sp: ", nspecies, 
                                "\nSeq: ", total_sequences)) %>%
          group_by(superkingdom) %>% mutate(y = max(y)*0.7)
sequences_data <- text_labels %>% group_by(superkingdom, kingdom) %>% summarise()
sequences_backgrounds <- c(lapply(unique(sequences_data$superkingdom), function(x) { element_rect(fill = plotColors[[as.character(x)]]) }))

p4 <- ggplot(taxonomydata, aes(x = kingdom, y = sequences, fill = kingdom)) +
          geom_boxplot(outlier.shape = NA) +
          geom_jitter(width = 0.2, alpha = 1, shape=21, color="black") +
          geom_label(data=text_labels, mapping=aes(y=y, label=label), size=4, alpha=.3) +
          scale_fill_manual(name = "Kingdom",
                            values = plotColors) +
                                      # c("Viridiplantae" = plotColors[["Viridiplantae"]],
                                      # "Metazoa" = plotColors[["Metazoa"]], 
                                      # "Fungi" = plotColors[["Fungi"]], 
                                      # "Unknown" = plotColors[["Unknown"]])) +
          geom_hline(yintercept=0, color="grey") +
          labs(title = "Sequences (per species) distribution per Kingdom") +
          ylab("Sequences per species") +
          facet_grid2(superkingdom~., scales = "free_y",
                      strip = strip_themed(
                        background_y = sequences_backgrounds,
                        text_y = list(element_text(colour = "white", size=12, hjust=0.5, face = "bold")))) +
          theme_minimal() +
          theme(legend.position = "none",
                axis.title.x = element_blank(),
                axis.text.x = element_text(size=14),
                plot.margin = margin(t=0, r=0, b=0, l=0, unit="pt"),
                plot.title = element_text(size=20, face="bold")) +
          labs(caption="Only species with at least 1 active sequence with verified motifs are taken into consideration for this plots\nSp=Species; Seq=Sequences")
p4
        
        
        
# HMM plot
#levels(hmmData$hmm) <- factor(hmmData$hmm, levels = rev(hmmData$hmm))
p5 <- ggplot(hmmData, aes(x = 1, y = n, fill = hmm)) +
          geom_bar(stat = "identity", width = .5, color="black", show.legend = FALSE) +
          geom_label_repel(aes(label = label, y = y), size=3, direction = "y", force_pull = 0, force = .3, show.legend = FALSE) +
          xlim(c(-4, 4)) +
          scale_y_reverse(expand = expansion(mult = c(0, 0))) +
          coord_flip() +
          theme_void() +
          theme(plot.title = element_text(size=20, face="bold")) +
          labs(title = "HMMs in TRACEY",
               plot.margin = margin(t=0, r=0, b=0, l=0, unit="pt"))
p5



# Motifs plot
motifs_labels <- motifsData %>%
          group_by(superkingdom, kingdom, motifName) %>%
          mutate(active_sequences = sum(sequenceActive),
                 total_sequences = length(sequenceActive)) %>%
          select(superkingdom, kingdom, motifName, active_sequences, total_sequences) %>% unique()
background_data <- motifs_labels %>% group_by(superkingdom, kingdom) %>% summarise()
motifs_backgrounds <- c(lapply(background_data$kingdom,      function(x) { element_rect(fill = plotColors[[as.character(x)]]) }),
                        lapply(background_data$superkingdom, function(x) { element_rect(fill = plotColors[[as.character(x)]]) }))
p6 <- ggplot(motifs_labels, aes(x = motifName, y = total_sequences, fill = motifName)) +
          geom_bar(stat = "identity", show.legend = FALSE, alpha=.3) +
          geom_bar(mapping = aes(y=active_sequences), stat = "identity", show.legend = FALSE) +
          scale_alpha_manual(name = "Sequence status",
                             values = c(.3, 1)) +
          # New filling scale for labels      
          new_scale_fill() +
          geom_label(aes(fill=log(total_sequences), label = total_sequences, y = max(total_sequences)*.9), size=3) +
          scale_fill_gradient2(low="#00A600", high="#FFA9C0", mid="#E6E600", midpoint = 5) +
          geom_hline(yintercept=0, color="grey") +
          facet_wrap2(vars(superkingdom, kingdom),
                      ncol = 1, #scale = "free_y",
                      strip.position = "right",
                      strip = strip_themed(
                        background_y = motifs_backgrounds,
                        text_y = list(element_text(colour = "white", size=14, hjust=0.5, face = "bold")))) +
          theme_minimal() +
          theme(panel.grid = element_blank(),
                axis.title.x = element_blank(),
                axis.title.y = element_blank(),
                axis.ticks.y = element_blank(),
                axis.text.x = element_text(size=14, angle=45, hjust=1, vjust=1),
                axis.line.y = element_line(color="black"),
                plot.title = element_text(size=20, face="bold"),
                legend.position = "none") +
          labs(title = "Number of motifs per Kingdom")
p6



layout <- "11AAABBBBEEEE
           11AAABBBBFFFF
           11AAABBBBFFFF
           ##AAABBBBFFFF
           #####BBBBFFFF
           DDDDDDDDDFFFF
           DDDDDDDDDFFFF
           DDDDDDDDDFFFF
           DDDDDDDDDFFFF"

p013 <- free(p0, type = "panel") + p1 + p3 + plot_layout(design = "AAACCCC
                                                                   BBBCCCC
                                                                   BBBCCCC
                                                                   BBBCCCC
                                                                   BBBCCCC
                                                                   BBBCCCC")
guide_area() + p013 + p2 + p4 + free(p5) + p6 + plot_layout(design = layout, guides = "collect") & theme(legend.box.margin = margin(10,10,10,10, unit = "pt"),
                                                                                                   legend.box.background = element_rect(colour = "black"))



















################ Sequences & Motifs updates
# Load sequences data
keep_columns <- c("sequence_id", "sequenceShortname", "sequenceStatus")

new_seqs <- read.csv('./utils/stats/sequences_query.tsv', sep='\t', header=TRUE, stringsAsFactors=TRUE)
new_seqs <- new_seqs[, keep_columns]
new_seqs$sequenceShortname <- as.character(new_seqs$sequenceShortname)
new_seqs[new_seqs$sequenceShortname == "", "sequenceShortname"] <- "Unknown"

old_seqs <- read.csv('./utils/stats/sequences_queryOld.tsv', sep='\t', header=TRUE, stringsAsFactors=TRUE)
old_seqs <- old_seqs[, keep_columns]
old_seqs$sequenceShortname <- as.character(old_seqs$sequenceShortname)
old_seqs[old_seqs$sequenceShortname == "", "sequenceShortname"] <- "Unknown"

seqs <- merge(old_seqs, new_seqs, by="sequence_id", all=TRUE) %>%
            mutate(sequenceShortname.x = as.character(sequenceShortname.x),
                   statusOld = as.character(sequenceStatus.x),
                   sequenceShortname.y = as.character(sequenceShortname.y),
                   statusNew = as.character(sequenceStatus.y),
                   change_status = paste0(statusOld, "_", statusNew)) %>%
            replace_na(list(sequenceShortname.x = "Not present", statusOld = "Not present",
                            sequenceShortname.y = "Not present", statusNew = "Not present")) %>%
            select(change_status, statusOld, statusNew) %>%
            group_by(change_status) %>%
            mutate(counts = sum(length(change_status))) %>% 
            unique()
seqs

ignore_classes <- c('ignore_ignore', 'live_live', "_")
al1 <- ggplot(#seqs[!(seqs$change_status %in% c('ignore_ignore', 'live_live', "_")) & grepl(pattern = "_live", x=seqs$change_status), ],
              seqs[!(seqs$statusOld == seqs$statusNew), ],
              aes(y=counts, axis1=statusOld, axis2=statusNew)) +
            geom_alluvium(aes(fill=statusOld), color="black", linewidth=0.2) +
            geom_stratum(aes(fill=after_stat(stratum)), width = 1/12, color = "black") +
            geom_label(aes(label = paste0(after_stat(stratum))),  stat = "stratum", fill="white", color="black") +
            
            scale_x_discrete(limits = c("statusOld", "statusNew"), expand = c(.1, .1)) +
            scale_fill_viridis_d() +
            theme_minimal()
al1
