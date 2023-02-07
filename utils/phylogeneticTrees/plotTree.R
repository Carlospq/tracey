library("ape", quietly = TRUE)
library("ggplot2", quietly = TRUE)
library("ggtree", quietly = TRUE)

args = commandArgs(trailingOnly=TRUE)

nwk <- args[1]
colname <- args[2]
groupNames <- args[3:length(args)]

tree <- read.tree(file = paste0('apps/static/assets/img/tmpTrees/', nwk))
unlink(paste0('apps/static/assets/img/tmpTrees/', nwk))

groupInfo <- split(tree$tip.label, sapply(strsplit(tree$tip.label, "\\|"), "[", 2))
groupInfo <- groupInfo[names(groupInfo) %in% groupNames == TRUE]

treeOTU <- groupOTU(tree, groupInfo)
group_nodes <- lapply(groupInfo, function(x) { getMRCA(treeOTU, x) })
treeOTU$tip.label <- sapply(strsplit(treeOTU$tip.label, "\\|"), "[", 1)

# Tree - Circular layout
tree_plot <- ggtree(treeOTU, aes(color=group), layout='circular') +
  ggtitle("TRACEY phylogeny", ) +
  geom_tiplab(size=5, offset = 2, show.legend = FALSE) +
  theme(legend.position = "right",
        legend.text = element_text(size = 12),
        legend.title = element_text(size = 15),
        legend.background = element_rect(fill="lightgrey", size=0.5, linetype="solid"),
        plot.title = element_text(hjust = 0.5, size = 18)) +
  guides(color=guide_legend(title=colname, override.aes=list(shape = 18)))


# Add clade labels
plotdata <- ggplot_build(tree_plot)
tree_plot_wClades <- tree_plot
n <- 0
for (label in names(group_nodes)){
  n <- n+1
  if (label=="Unclassified"){next}
  tree_plot_wClades <- tree_plot_wClades + geom_cladelabel(node=group_nodes[label][[1]], 
                                                           label=label,
                                                           fontsize = 0,
                                                           barsize=0.5,
                                                           offset=0.5, 
                                                           offset.text=5,
                                                           align=T,
                                                           angle="auto",
                                                           color=plotdata$data[[1]][plotdata$data[[1]]$node==group_nodes[label][[1]],]$colour
  )
}

# Plot tree
plotFileName <- paste0('apps/static/assets/img/tmpTrees/', nwk, '.png')
png(file=plotFileName, width=1400, height=1000)
print(tree_plot_wClades)
dev.off()
