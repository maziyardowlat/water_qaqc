library(shiny)
library(shinyjs)
library(DT)

options(shiny.maxRequestSize = 50 * 1024^2)

ui <- fluidPage(
  useShinyjs(),
  titlePanel("CSV Data Viewer with Column Renaming and Metadata"),
  
  sidebarLayout(
    sidebarPanel(
      fileInput("file1", "Choose CSV File",
                accept = c(
                  "text/csv",
                  "text/comma-separated-values,text/plain",
                  ".csv")
      ),
      numericInput("skip_rows", "Rows to Skip:", 1, min = 0),
      uiOutput("column_selector"),
      uiOutput("column_renamer"),
      
      # New Metadata Input Section
      h4("Metadata"),  # Add a section header
      textInput("station_code", "Station Code:", value = ""),
      textInput("logger_serial", "Logger Serial Number:", value = ""),
      numericInput("utc_offset", "UTC Offset:", value = 0),
      numericInput("data_id", "Data ID:", value = 0),
      
      actionButton("save_button", "Save Table") 
    ),
    
    mainPanel(
      DTOutput("contents")
    )
  )
)

server <- function(input, output, session) {
  
  structured_data <- reactiveVal(NULL)
  
  all_steps_completed <- reactiveVal(FALSE)
  
  # Filtered Data (Reactive)
  filtered_data <- reactive({
    req(input$file1, input$skip_rows)
    df <- read.csv(input$file1$datapath, skip = input$skip_rows)
    df[apply(df, 1, function(row) !any(row == "Logged")), , drop = FALSE] 
  })
  
  # Column Selector
  output$column_selector <- renderUI({
    req(filtered_data())
    checkboxGroupInput("selected_columns", "Select Columns to Keep:",
                       choices = names(filtered_data()),
                       selected = names(filtered_data()))
  })
  
  # Column Renamer
  output$column_renamer <- renderUI({
    req(filtered_data(), input$selected_columns)
    selected_columns <- filtered_data()[, input$selected_columns, drop = FALSE]
    lapply(names(selected_columns), function(colname) {
      selectInput(paste0("rename_", colname), label = paste("Rename", colname),
                  choices = c(colname, "timestamp", "wtmp"), 
                  selected = colname)
    })
  })
  
  # Track Completion of Steps
  observe({
    req(input$file1, input$skip_rows, !is.null(input$selected_columns))
    any_rename_inputs_empty <- any(sapply(names(input), function(x) startsWith(x, "rename_") && is.null(input[[x]])))
    all_steps_completed(!any_rename_inputs_empty)
  })
  
  # Enable/Disable Save Button
  observeEvent(all_steps_completed(), {
    if (all_steps_completed()) {
      shinyjs::enable("save_button")
    } else {
      shinyjs::disable("save_button")
    }
  })
  
  # Render Data Table
  output$contents <- renderDT({
    req(filtered_data(), input$selected_columns)
    df <- filtered_data()[, input$selected_columns, drop = FALSE]
    
    # Rename selected columns (if any)
    for (colname in names(df)) {
      new_name <- input[[paste0("rename_", colname)]]
      if (new_name != colname) {
        names(df)[names(df) == colname] <- new_name
      }
    }
    
    datatable(df)
  })
  
  # Save Table on Button Click
  observeEvent(input$save_button, {
    req(filtered_data(), input$selected_columns)
    
    df <- filtered_data()[, input$selected_columns, drop = FALSE]
    
    # Rename selected columns (if any)
    for (colname in names(df)) {
      new_name <- input[[paste0("rename_", colname)]]
      if (new_name != colname) {
        names(df)[names(df) == colname] <- new_name
      }
    }
    
    # Add Metadata Columns (even if empty)
    metadata_cols <- c("station_code", "logger_serial", "utc_offset", "data_id")
    for (col in metadata_cols) {
      df[[col]] <- input[[col]]
    }
    
    # Save to the global environment
    assign("structured_data", df, envir = .GlobalEnv)
    
    # Display a confirmation message
    showModal(modalDialog(
      title = "Data Saved",
      "Raw Data has been formatted. Closing app...",
      easyClose = TRUE
    ))
    # Stop the app after a short delay
    Sys.sleep(2) 
    stopApp()
  })
}

shinyApp(ui = ui, server = server)

