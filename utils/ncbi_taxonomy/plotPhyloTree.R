library("ape", quietly = TRUE)
library("ggplot2", quietly = TRUE)
library("ggtree", quietly = TRUE)

nwk <- 'utils/ncbi_taxonomy/TRACEY_phylogeneticTree.newick'
tree <- read.tree(file = nwk)
groupInfo <- split(tree$tip.label, sapply(strsplit(tree$tip.label, "\\|"), "[", 2))
groupInfo <- groupInfo[names(groupInfo) %in% "outer" == FALSE]
#Add number of taxas to tag label
for (i in 1:length(names(groupInfo)) ){
  names(groupInfo)[[i]] <- paste0(names(groupInfo)[[i]], "\n", "(", length(groupInfo[[i]]), ")")
}
treeOTU <- groupOTU(tree, groupInfo)
group_nodes <- lapply(groupInfo, function(x) { getMRCA(treeOTU, x) })


# Tree - Circular layout
tree_plot <- ggtree(treeOTU, aes(color=group), layout='circular') +
                  ggtitle("TRACEY phylogeny", ) +
                  #geom_tiplab(size=1) +
                  theme(legend.position = "none",
                        plot.title = element_text(hjust = 0.5, size = 18)) 


# Add clade labels
plotdata <- ggplot_build(tree_plot)
tree_plot_wClades <- tree_plot
n <- 0
for (label in names(group_nodes)){
  n <- n+1
  if (label=="Unclassified"){next}
  tree_plot_wClades <- tree_plot_wClades + geom_cladelabel(node=group_nodes[label][[1]], 
                                                           label=label,
                                                           fontsize = 6,
                                                           barsize=0.5,
                                                           offset=1, 
                                                           offset.text=4,
                                                           align=T,
                                                           angle="auto",
                                                           color=plotdata$data[[1]][plotdata$data[[1]]$node==group_nodes[label][[1]],]$colour
                                                           )
}

# Plot tree
#tree_plot_wClades
pdf(file="utils/ncbi_taxonomy/TRACEY_phylogeneticTree.pdf", width = 15, height = 15)
print(tree_plot_wClades)
dev.off()

png(file="apps/static/assets/img/images/TRACEY_phylogeneticTree.png", width=800, height=800)
print(tree_plot_wClades)
dev.off()

  
# Get subtree from node number
# subtree <- extract.clade(tree, 73085)
# ggtree(subtree, layout='circular')








