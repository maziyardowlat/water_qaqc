library(shiny)
library(DT)
library(plotly)

# Data in Review:
data <- dat_raw_review %>%
  dplyr::reframe(timestamp, wtmp, wtmp_flag)

ui <- fluidPage(
  titlePanel("QA/QC Data Review"),
  
  sidebarLayout(
    sidebarPanel(
      selectInput("selected_flag", "Select Flag:", choices = unique(data$wtmp_flag)),
      textAreaInput("qaqc_notes", "QA/QC Notes:", rows = 25),
      actionButton("save_notes", "Data Reviewed")
    ),
    
    mainPanel(
      DT::dataTableOutput("filtered_table"),
      plotlyOutput("interactive_plot")
    )
  )
)

server <- function(input, output) {
  
  filtered_data <- reactive({
    data[data$wtmp_flag == input$selected_flag, ]
  })
  
  output$filtered_table <- DT::renderDataTable({
    filtered_data()
  })
  
  output$interactive_plot <- renderPlotly({
    fig <- plot_ly(data, x = ~timestamp, y = ~wtmp, type = 'scatter', mode = 'markers') %>%
      add_trace(data = filtered_data(), marker = list(color = 'yellow')) %>%
      layout(title = "Selected Flag Data") 
    fig
  })
  
  # Observer for the "Data Reviewed" button
  observeEvent(input$save_notes, {
    notes_text <- input$qaqc_notes
    assign("qaqc_notes", notes_text, envir = .GlobalEnv)
    
    # Display a confirmation message
    showModal(modalDialog(
      title = "Data Saved",
      "Data has been reviewed. Closing app...",
      easyClose = TRUE
    ))
    # Stop the app after a short delay
    Sys.sleep(2) 
    stopApp()
  })
  
}

shinyApp(ui = ui, server = server)

