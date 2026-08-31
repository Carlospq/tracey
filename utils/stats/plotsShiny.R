# Set WD
setwd('C:/Users/cpulidoq/Documents/traceyDB/')

# Install & load packages
packages <- c("shiny", "bslib", "dplyr", "tidyr", "ggplot2", "ggalluvial", "viridis")

# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())
if (any(installed_packages == FALSE)) {
  install.packages(packages[!installed_packages])
}

# Packages loading
invisible(lapply(packages, library, character.only = TRUE))


# Load sequences & motifs data
keep_columns <- c("sequence_id", "sequenceShortname", "sequenceStatus")

new_seqs <- read.csv('./utils/stats/sequences_query.tsv', sep='\t', header=TRUE, quote="")
new_seqs <- new_seqs[, keep_columns]
new_seqs$sequenceShortname <- as.character(new_seqs$sequenceShortname)
new_seqs[new_seqs$sequenceShortname == "", "sequenceShortname"] <- "Unknown"

old_seqs <- read.csv('./utils/stats/sequences_queryOld.tsv', sep='\t', header=TRUE, quote="")
old_seqs <- old_seqs[, keep_columns]
old_seqs$sequenceShortname <- as.character(old_seqs$sequenceShortname)
old_seqs[old_seqs$sequenceShortname == "", "sequenceShortname"] <- "Unknown"

new_motifs_df <- read.csv('./utils/stats/motifs_query.tsv', sep='\t', header=TRUE, quote="") 
old_motifs_df <- read.csv('./utils/stats/motifs_queryOld.tsv', sep='\t', header=TRUE, quote="")


new_motifs_df <- merge(new_seqs, new_motifs_df, by="sequence_id", all=TRUE) %>% 
                    select(sequence_id, motifname, sequenceShortname, sequenceStatus) %>%
                    group_by(sequence_id, motifname) %>%
                    mutate(n = n(),
                           motifname = ifelse(is.na(motifname), "No motifs", motifname)) %>%
                    unique()
old_motifs_df <- merge(old_seqs, old_motifs_df, by=c("sequence_id"), all=TRUE) %>% 
                    select(sequence_id, motifname, sequenceShortname, sequenceStatus) %>%
                    group_by(sequence_id, motifname) %>%
                    mutate(n = n(),
                           motifname = ifelse(is.na(motifname), "No motifs", motifname)) %>%
                    unique()


df <- merge(old_motifs_df, new_motifs_df, by=c("sequence_id", "motifname"), all=TRUE) %>%
          mutate(sequenceShortname.x = as.character(sequenceShortname.x),
                 statusOld = as.character(sequenceStatus.x),
                 sequenceShortname.y = as.character(sequenceShortname.y),
                 statusNew = as.character(sequenceStatus.y)) %>%
          replace_na(list(sequenceShortname.x = "Not present", statusOld = "Not present",
                          sequenceShortname.y = "Not present", statusNew = "Not present")) %>%
          mutate(change_status = paste0(statusOld, "_", statusNew)) %>%
          select(sequence_id, sequenceShortname.x, motifname, n.x, change_status, statusOld, statusNew)


# Define UI
ui <- page_sidebar(
      
        sidebar = sidebar(
            
                      checkboxGroupInput(
                        "var0", "Motif",
                        choices = unique(df$motifname), 
                        selected = "SNARE"
                      ),
          
                      checkboxGroupInput(
                        "var1", "Old status",
                        choices = unique(df$statusOld), 
                          selected = unique(df$statusOld)
                      ),
                      
                      checkboxGroupInput(
                        "var2", "New status",
                        choices = unique(df$statusNew), 
                        selected = unique(df$statusNew)
                      ),
                      
                      checkboxGroupInput(
                        "var3", "Change status",
                        choices = unique(df$change_status), 
                        selected = unique(df$change_status[!(df$change_status %in% c("live_live", "ignore_ignore", "_"))])
                      ),
                      
                      width = 400
                      
                  ),
          
        plotOutput("scatter")
          
      )

# Define server logic
server <- function(input, output, session) {
  
              subsetted <- reactive({
                req(input$var1)
                req(input$var2)
                df |> filter(motifname %in% input$var0) |> 
                      filter(statusOld %in% input$var1) |> 
                      filter(statusNew %in% input$var2) |> 
                      filter(change_status %in% input$var3) |>
                      filter(!(change_status == "_")) |>
                      select(statusOld, statusNew, change_status) |>
                      group_by(change_status, statusOld, statusNew) %>%
                      summarise(counts = n()) %>% 
                      unique()
              })
              
              output$scatter <- renderPlot({
                ggplot(subsetted(), aes(y=counts, axis1=statusOld, axis2=statusNew)) +
                    geom_alluvium(aes(fill=statusOld), color="black", linewidth=0.2) +
                    geom_stratum(aes(fill=after_stat(stratum)), width = 1/12, color = "black") +
                    geom_label(aes(label = paste0(after_stat(stratum), ": ", after_stat(count))),  stat = "stratum", fill="white", color="black") +
                    
                    scale_x_discrete(limits = c("statusOld", "statusNew"), expand = c(.1, .1)) +
                    scale_fill_viridis_d() +
                    theme_minimal()
                }, res = 100)
              
}

# Run the application
shinyApp(ui = ui, server = server)

