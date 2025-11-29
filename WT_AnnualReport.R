################
#AnnualReport.r
#2024-12-13
#Justin kokoszka
################

#This code combines all data records for a station and creates a 
#comprehensive annual data report.

### ALL data must have a utc_offset = 0; averaging multiple loggers is dependent.

# Required Packages -------------------------------------------------------
library(dplyr)
library(readxl)
library(lubridate)
library(imputeTS)
library(fasstr)
library(rmarkdown)
library(ggplot2)

# Defined Variables and Functions -----------------------------------------
# User defined:
username <- "dowlataba"
station_code <- "02FW006"
today <- format(Sys.Date(), "%Y-%m-%d")
field_season_year <- 2025

# Create directories:
user_dir <- paste0("C:/Users/", username, "/UNBC/NHG Field - Data Management")

folder_path <- paste0(user_dir, "/02_Stations/", station_code, "*")
matching_folder <- Sys.glob(folder_path)

if (length(matching_folder) == 0) {
  stop(paste("No folder found for station code:", station_code))
}

dat_dir <- paste0(matching_folder)

# Defined Functions:
#Function to read metabase tables:
read_excel_sheet <- function(file_path, sheet_name) {
  tryCatch(
    {
      df <- read_excel(file_path, sheet = sheet_name)
      return(df)
    },
    error = function(e) {
      message(paste("Warning: Sheet", sheet_name, "not found or could not be read."))
      return(NULL)
    }
  )
}

# Data Acquisition and Preparation ----------------------------------------
#Compile all records:
# Obtain all tidy csv files:
tidy_files <- list.files(
  path = paste0(matching_folder, "/01_Data/02_Tidy/"),
  pattern = paste0("^(", paste(station_code, collapse = "|"), ")_.*_\\d{8}\\.csv"),
  full.names = TRUE
)

# Initialize and empty data frame to host the historical records:
dat_historical <- data.frame()

# Loop through each tidy file, read it, and append to the historical data frame
for (file in tidy_files) {
  # Read the CSV file
  temp_data <- read.csv(file) %>%
    dplyr::mutate(timestamp = lubridate::parse_date_time(timestamp, orders = "ymd HMS"),
                  timestamp = lubridate::force_tz(timestamp, tz = "UTC"))
  # Append to the historical data frame
  dat_historical <- bind_rows(dat_historical, temp_data) %>%
    dplyr::arrange(timestamp)
}

# Convert historical serial_logger to character:
dat_historical <- dat_historical %>%
  dplyr::mutate(logger_serial = as.character(logger_serial),
                data_id = as.character(data_id))

# Initial Investigation: --------------------------------------------------
# Check if there is more than one unique station code
multiple_stations <- length(unique(dat_historical$station_code)) > 1

# Print the result
if (multiple_stations) {
  print("The dataset contains more than one station code.")
} else {
  print("The dataset contains only one station code.")
  print(unique(dat_historical$station_code))
}

# Extract station code:
station_code <- unique(dat_historical$station_code)

# Check that all utc offsets are 0:
if (any(dat_historical$utc_offset != 0)) {
  stop(paste("UTC Offset is not 0!"))
}

# Check for duplicated values:
first_anyDuplicated <- anyDuplicated(dat_historical$timestamp)

if (first_anyDuplicated > 0) {
  stop(paste("Duplicated timestamps in data. Check for multiple loggers!"))
}

# List loggers:
list_loggers <- unique_names <- unique(dat_historical$logger_serial)
print(list_loggers)

# Plot logger data:
p1 <- ggplot2::ggplot(dat_historical,
                      ggplot2::aes(x = timestamp,
                                   y = wtmp,
                                   color = logger_serial)) +
  ggplot2::geom_line() +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = station_code) +
  ggplot2::theme_bw()

print(p1)

# Deal with multiple loggers: ---------------------------------------------
###Currently this only works when two data loggers overlap!!!

# Average out multiple logger records:
# Identify duplicates:
duplicates <- dat_historical %>%
  dplyr::group_by(timestamp) %>%
  dplyr::filter(n_distinct(logger_serial) > 1)
print(duplicates)

# Calculate averages:
# All duplicated values pass, take the averaged value:
duplicated_allP <- duplicates %>%
  dplyr::group_by(timestamp) %>%
  dplyr::filter(all(wtmp_flag == "P")) %>%
  dplyr::mutate(wtmp = mean(wtmp),
                logger_serial = paste(logger_serial, collapse = "."),
                data_id = paste(data_id, collapse = "."),
                wtmp_flag = "A") %>%
  dplyr::ungroup() %>%
  dplyr::distinct()

# One duplicated value passed, take the passed value:
duplicated_oneP <- duplicates %>%
  dplyr::group_by(timestamp) %>%
  dplyr::filter(any(wtmp_flag != "P")) %>%
  dplyr::mutate(wtmp = ifelse(wtmp_flag == "P", wtmp, NA)) %>%
  dplyr::filter(!is.na(wtmp)) %>%
  dplyr::ungroup() %>%
  dplyr::distinct()

# Check if duplicates still remain:
anyDuplicated_oneP <- anyDuplicated(duplicated_oneP$timestamp)

if (anyDuplicated_oneP > 0) {
  stop(" Duplicates!!! Need a solution for this one!") 
} else {
  print("No remaining duplicates!")
}

# Both duplicated values flagged, average and flag with caution:
duplicated_noP <- duplicates %>%
  dplyr::group_by(timestamp) %>%
  dplyr::filter(all(wtmp_flag != "P")) %>%
  dplyr::mutate(wtmp = ifelse(all(is.na(wtmp)), NA, mean(wtmp, na.rm = T)),
                logger_serial = paste(logger_serial, collapse = "_"),
                data_id = paste(data_id, collapse = "."),
                wtmp_flag = ifelse(all(wtmp_flag == "M"), "M", "C")) %>%
  dplyr::distinct() %>%
  dplyr::ungroup()

# Combine averages data:
dat_clean <- dat_historical %>%
  filter(!(timestamp %in% duplicates$timestamp)) %>%
  bind_rows(duplicated_allP) %>%
  bind_rows(duplicated_oneP) %>%
  bind_rows(duplicated_noP) %>%
  arrange(timestamp)

# Check for duplicates:
second_anyDuplicated <- anyDuplicated(dat_clean$timestamp)

if (second_anyDuplicated > 0) {
  stop(" Duplicates!!! Unsuccessful logger merge!") 
} else {
  print("Logger merge successful!")
}

# Print duplicated timestamps: 
anyDuplicated(dat_clean$timestamp)
duplicated_indices <- duplicated(dat_clean$timestamp)
duplicated_timestamps <- dat_clean$timestamp[duplicated_indices]
print(duplicated_timestamps)

 # Print duplicated data from historical data:
dup_historical <- dat_historical %>%
  dplyr::filter(timestamp %in% duplicated_timestamps) %>%
  dplyr::distinct(data_id, logger_serial)

print(dup_historical)

# Check the data is continuous:
expected_timestamps <- seq(from = min(dat_historical$timestamp), 
                           to = max(dat_historical$timestamp), 
                           by = "15 mins")

# Check if all expected timestamps are present in the data
all_present <- all(expected_timestamps %in% dat_clean$timestamp)

# Print statement
if (all_present) {
  print("Data is continuous with 15-minute intervals.")
} else {
  print("Data is NOT continuous with 15-minute intervals!!!!")
  #Maria: added the code below to help me find missing timestamps
  missing_timestamps <- setdiff(expected_timestamps, dat_clean$timestamp)
  missing_timestamp_converted <- as.POSIXct(missing_timestamps, origin = "1970-01-01", tz = "UTC")
  print(paste("Missing timestamp(s):",missing_timestamp_converted))
}

# Metadata Extraction: ----------------------------------------------------
# Collect all meta records:
meta_file_path <- paste0(user_dir, "/01_Metabase/CoreDataTables.xlsx")

# Site details:
metaSheet_site <- "Sites"
dat_sites <- read_excel_sheet(meta_file_path, metaSheet_site) %>%
  dplyr::filter(Site_code == station_code) %>%
  dplyr::select(-c("Site_ID", "Site_contact", "GPS_Link"))

# Visit details:
metaSheet_visit <- "Visits"
dat_visits <- read_excel_sheet(meta_file_path, metaSheet_visit) %>%
  dplyr::filter(Site_code == station_code) %>%
  dplyr::arrange(Visit_date)

# Equipment details:
metaSheet_deployments <- "Deployments"
dat_deployments <- read_excel_sheet(meta_file_path, metaSheet_deployments) %>%
  dplyr::filter(Site_code == station_code) %>%
  dplyr::arrange(Deploy_date) %>%
  dplyr::select(c("Equip_code", "Logger_code", "Deploy_date",
                  "Deploy_height (cm)", "Retrieval_date", "Retreival_reason"))

# Data details:
metaSheet_data <- "Data"
dat_data <- read_excel_sheet(meta_file_path, metaSheet_data) %>%
  dplyr::filter(Site_code == station_code) %>%
  dplyr::select(-c("Data_linkRaw", "Data_linkQAQC", "QAQC_notes"))

dat_qaqcNotes <- read_excel_sheet(meta_file_path, metaSheet_data) %>%
  dplyr::filter(Site_code == station_code) %>%
  dplyr::select(c("Data_ID", "QAQC_notes"))

#3. Extract report data:
timestamp_first <- head(dat_clean$timestamp, 1)
timestamp_last <- tail(dat_clean$timestamp, 1)
record_length <- length(dat_clean$timestamp)

# Extract flag data:
flag_counts <- table(dat_clean$wtmp_flag)
flag_proportions <- prop.table(flag_counts)
flag_table <- data.frame(
  wtmp_flag = names(flag_counts),
  count = as.numeric(flag_counts),
  proportion = round(as.numeric(flag_proportions*100),2))

# Summary statistics:
# Summary for all values:
wtmp_summary_all <- dat_clean %>%
  summarise(
    across(wtmp, list(
      mean = ~mean(.x, na.rm = TRUE),
      sd = ~sd(.x, na.rm = TRUE),
      min = ~min(.x, na.rm = TRUE),
      max = ~max(.x, na.rm = TRUE),
      median = ~median(.x, na.rm = TRUE),
      p25 = ~quantile(.x, 0.25, na.rm = TRUE),
      p75 = ~quantile(.x, 0.75, na.rm = TRUE),
      p5 = ~quantile(.x, 0.05, na.rm = TRUE),
      p95 = ~quantile(.x, 0.95, na.rm = TRUE)
    ), .names = "{.fn}_all"),
    n = n())

# Summary for passed values:
wtmp_summary_p <- dat_clean %>%
  dplyr::filter(wtmp_flag == "P") %>%
  dplyr::summarise(
    across(wtmp, list(
      mean = ~mean(.x, na.rm = TRUE),
      sd = ~sd(.x, na.rm = TRUE),
      min = ~min(.x, na.rm = TRUE),
      max = ~max(.x, na.rm = TRUE),
      median = ~median(.x, na.rm = TRUE),
      p25 = ~quantile(.x, 0.25, na.rm = TRUE),
      p75 = ~quantile(.x, 0.75, na.rm = TRUE),
      p5 = ~quantile(.x, 0.05, na.rm = TRUE),
      p95 = ~quantile(.x, 0.95, na.rm = TRUE)
    ), .names = "{.fn}_P"),
    n = n())

# Data Visualization ------------------------------------------------------
# Plot flags:
p2 <- ggplot2::ggplot(dat_clean, aes(x = timestamp, y = wtmp)) +
  ggplot2::geom_line(color = "black") +
  ggplot2::geom_point(data = subset(dat_clean, wtmp_flag != "P"), aes(color = wtmp_flag)) + 
  ggplot2::geom_vline(data = subset(dat_clean, wtmp_flag == "M"),
                      aes(xintercept = timestamp), color = "indianred") +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = station_code) +
  ggplot2::theme_bw() +
  ggplot2::scale_color_manual(values = c(
    "N" = "#000000",
    "B" = "#4287f5", 
    "S" = "brown3",
    "E" = "mediumpurple2",
    "T" = "orange",
    "D" = "#8b4513",
    "V" = "lightseagreen",
    "A" = "#f5e342",
    "C" = "deeppink"))

print(p2)

# Plot annual plot with current year:
# Extract start/end periods:
timestamp_first <- head(dat_clean$timestamp, 1)
timestamp_last <- tail(dat_clean$timestamp, 1)

# Calculate daily mean
dat_daily <- dat_clean %>%
  dplyr::filter(wtmp_flag %in% c("P", "A", "V", "T", "C")) %>%
  dplyr::mutate(date = as.Date(timestamp)) %>%
  dplyr::group_by(date) %>%
  dplyr::summarise(wtmp_mean = {
      na_proportion <- mean(is.na(wtmp))
      if (na_proportion < 0.1) {
        mean(wtmp, na.rm = TRUE)
      } else {
        NA_real_
      }
    },
    .groups = "drop" # ungroup after summarise
  ) %>%
  dplyr::ungroup() %>%
  fasstr::fill_missing_dates(dates = date) %>%
  dplyr::filter(dplyr::between(date, as.Date(timestamp_first), as.Date(timestamp_last))) %>%
  dplyr::mutate(wtmp_7day = zoo::rollmean(wtmp_mean, k = 7, fill = NA, align = "center"))

# Extract data for the current year
current_year_data <- dat_daily %>%
  dplyr::filter(year(date) == field_season_year) %>%
  dplyr::mutate(day_of_year = lubridate::yday(date))

all_year_data <- dat_daily %>%
  dplyr::mutate(day_of_year = lubridate::yday(date)) %>%
  dplyr::group_by(day_of_year) %>%
  dplyr::summarise(wtmp_mean = mean(wtmp_7day, na.rm = T))

# Plot the data:
p3 <- ggplot2::ggplot() +
  ggplot2::geom_line(data = all_year_data,
                     ggplot2::aes(x = day_of_year, y = wtmp_mean, color = "All Years"),
                     linewidth = 0.8) +
  ggplot2::geom_line(data = current_year_data, 
                     ggplot2::aes(x = day_of_year, y = wtmp_7day, color = "Most Recent Year"),
                     linewidth = 0.8) +
  ggplot2::labs(x = "Month", y = "Temperature (°C)",
                title = "Daily mean water temperature",
                subtitle = station_code,
                color = NULL) +
  ggplot2::scale_color_manual(values = c("All Years" = "black", "Most Recent Year" = "blue")) +
  ggplot2::theme_bw() +
  ggplot2::theme(legend.position = "bottom") +
  ggplot2::scale_x_continuous(breaks = seq(15, 366, by = 30),
                              labels = month.abb)

print(p3)

# Save and export the data: -----------------------------------------------
dat_clean$timestamp <- format(dat_clean$timestamp, "%Y-%m-%d %H:%M:%S",
                                   usetz = F)

# Save a csv:
write.csv(dat_clean,
          paste0(dat_dir, "/01_Data/03_compiled/", station_code,
                 "_compiled_", today, ".csv"), row.names = F)

# Write to data output:

# Save as rds:
rds_filename <- saveRDS(dat_clean,
                        file.path(paste0(dat_dir,
                                         "/01_Data/03_compiled/",
                                         station_code,
                                         "_compiled_",
                                         today,
                                         ".rds")))

# Generate Markdown Report: -----------------------------------------------
# Render R Markdown Document:
rmarkdown::render(paste0(user_dir, "/06_Scripts/WT_AnnualReportMarkdown.Rmd"),
                  output_dir = paste0(matching_folder, "/03_Reports/03_Annual"),
                  output_file = paste0(station_code, "_annualReport_",
                                       today))
####
#END
####

