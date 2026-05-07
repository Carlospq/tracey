library(dplyr)
library(ggplot2)
library(patchwork) 
library(colorspace)
library(ggrepel)

##### read data
df <- read.csv("C:/Users/cpulidoq/Documents/traceyDB/snare_sequences_per_taxa.tsv", sep="\t", header = FALSE)
#colnames(df) <- c('superkingdom', 'clade', 'kingdom', 'phylum', 'order', 'family', 'genus', 'species', 'count')
#colnames(df) <- c('kingdom', 'phylum', 'count')
colnames(df) <- c('superclass', 'class', 'count')
df <- df[df$count<200,]
df <- df %>%
  mutate(
    superclass = ifelse(is.na(superclass) | superclass == "", 
                     "None", 
                     superclass),
    class = ifelse(is.na(class) | class == "", 
                   "None", 
                   class)
  ) %>%
  mutate(
    superclass = ifelse(superclass == "Viridiplantae" | superclass == "Rhodophyta", 
                        "Viridiplantae-Rhodophyta", 
                        superclass)
  )
 
##### Distribution of species per #sequences 
ggplot(df, aes(x=count)) +
  geom_bar(fill="lightblue", color="darkblue") +
  geom_density(aes(y = ..density.. * 1000 * 0.8 ), colour = "red", fill="red", size=1, alpha=0.3) +
  scale_y_continuous(
    
    # Features of the first axis
    name = "# Species",
    
    # Add a second axis and specify its features
    sec.axis = sec_axis(~./800, name="Density")
  ) + 
  xlab("#SNARE sequences") +
  labs(title = "#Sequences per species") +
  theme_minimal() +
  theme(
    axis.title = element_text(size=14),
    axis.text = element_text(size=12),
    axis.text.y.right = element_text(color="red"),
  )


##### species with less than 20 sequences
nrow(df[df$count<20,])
df20 <- df[df$count<20,]

# Remove ophistokonta to plot smaller taxas
df20 <- df20[df20$superclass!="Opisthokonta",]


##### Prepare data for piechart
df20counts <- df20 %>%
  group_by(superclass, class) %>%
  mutate(id = paste0(superclass, "_", class),
         nsequences_per_class = sum(count)) %>%
  ungroup() %>% group_by(superclass) %>%
  mutate(nsequences_per_superclass = sum(count)) %>%
  group_by(superclass, class) %>%
  arrange(nsequences_per_superclass, nsequences_per_class, count) %>%
  select(superclass, class, id, nsequences_per_superclass, nsequences_per_class) %>% 
  unique() %>% ungroup()

## Data by circles
superclass <- df20counts %>%
  ungroup() %>% group_by(superclass) %>%
  select(superclass, nsequences_per_superclass) %>%
  unique() %>% ungroup()
superclass$superclass <- factor(superclass$superclass, levels = unique(superclass$superclass))

class <- df20counts %>%
  ungroup() %>% group_by(superclass, class) %>%
  select(id, class, nsequences_per_class) %>%
  unique() %>% ungroup()
class$id <- factor(class$id, levels = unique(class$id))


## Colors
palette_list <- list(
  "Bacteria"       = function(n) colorspace::sequential_hcl(n, palette = "YlOrBr"),
  "Viruses" = function(n) colorspace::sequential_hcl(n, palette = "Grays"),
  "Haptista"         = function(n) colorspace::sequential_hcl(n, palette = "YlGn"),
  "Malawimonadida"  = function(n) colorspace::sequential_hcl(n, palette = "Purples"),
  "Amoebozoa"  = function(n) colorspace::sequential_hcl(n, palette = "Reds 2"),
  "Metamonada"  = function(n) colorspace::sequential_hcl(n, palette = "OrRd"),
  "Rhodophyta"  = function(n) colorspace::sequential_hcl(n, palette = "BuPu"),
  "Discoba"  = function(n) colorspace::sequential_hcl(n, palette = "PuRd"),
  "Sar"  = function(n) colorspace::sequential_hcl(n, palette = "Blues"),
  "Viridiplantae"  = function(n) colorspace::sequential_hcl(n, palette = "Greens"),
  "Viridiplantae-Rhodophyta"  = function(n) colorspace::sequential_hcl(n, palette = "Greens"),
  "Opisthokonta"  = function(n) colorspace::sequential_hcl(n, palette = "Oranges"),
  "other entries" = function(n) colorspace::sequential_hcl(n, palette = "Light Grays")
)


class_colors <- class %>%
  group_by(superclass) %>%
  group_modify(~{
    k <- .y$superclass
    n <- nrow(.x)
    .x$color <- palette_list[[k]](n)
    .x
  }) %>%
  ungroup()
class_colors$id <- factor(class_colors$id, levels = unique(class_colors$id))

superclass_colors <- class_colors %>%
  group_by(superclass) %>%
  summarise(color = first(color), .groups = "drop")

## Labels
superclass$superclass <- factor(superclass$superclass, levels = unique(superclass$superclass))
superclass_labels <- superclass %>%
  mutate(
    total = sum(nsequences_per_superclass),
    ymax = cumsum(nsequences_per_superclass),
    ymin = lag(ymax, default = 0),
    label_pos = total - (ymax + ymin)/2 
  )

class$class <- factor(class$class, levels = unique(class$class))
class_labels <- class %>%
  mutate(
    total = sum(nsequences_per_class),
    ymax = cumsum(nsequences_per_class),
    ymin = lag(ymax, default = 0),
    label_pos = total - (ymax + ymin)/2 
  )


ggplot() +
  # Donuts
  geom_col( data = superclass, aes(x = 1, y = nsequences_per_superclass, fill = superclass), width = 1 ) +
  geom_col( data = class,  aes(x = 2, y = nsequences_per_class,  fill = id),  width = 0.3 ) +
  # Labels (#sequences per kingdom / phylum)
  geom_label_repel(
    data = superclass_labels,
    aes(x = 1, y = label_pos, label = paste0(superclass, "\n", nsequences_per_superclass) ),
    size = 4,
    hjust = .5,
    max.overlaps = 40
  ) +
  geom_label_repel(
    data = class_labels,
    aes(x = 2, y = label_pos, label = paste0(class, "\n", nsequences_per_class) ),
    size = 4,
    hjust = .5,
    max.overlaps = 20
  ) +
  # Colors
  scale_fill_manual(
    values = c(
      setNames(class_colors$color, class_colors$id),
      setNames(superclass_colors$color, superclass_colors$superclass)
    )
  ) +
  # Shape and Theme
  labs(title = "Number of SNARE sequences per Superclass (inner cercle) and class (outer cirlce)\n
       for species with less than 20 sequences") +
  coord_polar(theta = "y") +
  theme_void() +
  theme(legend.position = "None",
        plot.title = element_text(size = 18, hjust = .5))




