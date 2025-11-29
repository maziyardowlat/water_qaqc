#######
#Header
#######

# Required Packages -------------------------------------------------------
library(dplyr)
library(lubridate)
library(tidyverse)
library(RcppRoll)
library(ggplot2)
library(tidyr)
library(zoo)

# User defined variables: -------------------------------------------------
# User inputs:
username <- "dowlataba"
station_code <- "02FW006"
raw_fileDate <- "20250711"
logger_serial <- "4621"
data_id <- 267
utc_offset <- 0

Structured_data <- structured_data %>%
  dplyr::mutate(
    timestamp = lubridate::parse_date_time(timestamp, orders = "mdy HM"),
    timestamp = timestamp + lubridate::hours(7),
    timestamp = lubridate::force_tz(timestamp, tz = "UTC")
  )
#####STOP
#!!! Convert to UTC!!!
field_datetime_in <- "20250711 1715"
field_datetime_out <- "20250711 1930"
prevField_datetime_in <- "NULL" #NULL for first time visit (added these since missing)
prevField_datetime_out <- "NULL" #NULL for first time visit


######STOP
#!!!For logger swap, use last record from last logger:
#last_record <- lubridate::ymd_hm("20240128 0400")
#####Continue

# Create date time in/out formats:
datetime_in <- lubridate::ymd_hm(field_datetime_in, tz = "UTC")
datetime_out <- lubridate::ymd_hm(field_datetime_out, tz = "UTC")
prev_datetime_in <- lubridate::ymd_hm(prevField_datetime_in, tz = "UTC")
prev_datetime_out <- lubridate::ymd_hm(prevField_datetime_out, tz = "UTC")

# Create directories:
user_dir <- paste0("C:/Users/", username, "/OneDrive - UNBC/NHG Field - Data Management")
folder_path <- paste0(user_dir, "/02_Stations/", station_code, "*")
matching_folder <- Sys.glob(folder_path)

if (length(matching_folder) == 0) {
  stop(paste("No folder found for station code:", station_code))
}

dat_dir <- paste0(matching_folder)

# Read in historical data: -----------------------------------------------------
# Obtain all tidy csv files:
# Read in historical data: -----------------------------------------------------
tidy_files <- list.files(
  path = paste0(matching_folder, "/01_Data/02_Tidy/"),
  pattern = paste0(".*_(", paste(logger_serial, collapse = "|"), ")_\\d{8}\\.csv"), 
  full.names = TRUE
)

dat_historical <- data.frame()

for (file in tidy_files) {
  # 1. Read as raw text, don't convert anything yet
  temp_data <- read.csv(file, stringsAsFactors = FALSE, check.names = FALSE)
  # 2. FORCE LOWERCASE HEADERS (Fixes "Timestamp" vs "timestamp" mismatch)
  colnames(temp_data) <- tolower(colnames(temp_data))
  # Check if timestamp exists after lowercasing
  if (!"timestamp" %in% colnames(temp_data)) {
    warning(paste("Skipping file - 'timestamp' column missing in:", basename(file)))
    next
  }
  
  temp_data <- temp_data %>%
    dplyr::mutate(
      # 3. Clean the text: convert to character and remove leading/trailing spaces
      timestamp = as.character(timestamp),
      timestamp = stringr::str_trim(timestamp), 
      # 4. Try multiple formats (Including ones with seconds and without)
      timestamp = lubridate::parse_date_time(timestamp, 
                                             orders = c("mdy HM", "mdy HMS", "ymd HMS", "ymd HM", "dmy HM")),
      timestamp = lubridate::force_tz(timestamp, tz = "UTC")
    ) %>%
    # Remove rows where the timestamp failed to parse (NAs)
    dplyr::filter(!is.na(timestamp))
  
  dat_historical <- bind_rows(dat_historical, temp_data) %>%
    dplyr::arrange(timestamp)
}

# Raw time stamp QAQC: ---------------------------------------------------------
# Corrects time stamp format:
dat_raw <- Structured_data %>%
  dplyr::mutate(timestamp = lubridate::ceiling_date(timestamp, unit = "minute")) %>%
  dplyr::mutate(timestamp = lubridate::round_date(timestamp, unit = "15 minutes"))

if (tail(dat_raw$timestamp, n = 1) < datetime_in) {
  stop("Data incomplete - Check if battery died!")
}

# Raw data start and end dates:
hist_end <- tail(dat_historical$timestamp, n = 1)

#####STOP!!!
#!!! For first data set
# raw_start <- head(dat_raw$timestamp, n = 1)
#!!! For logger swap:
#raw_start <- last_record + lubridate::minutes(15)
#!!! For sequential data set
raw_start <- hist_end + lubridate::minutes(15)
#####CONTINUE!!!

raw_end <- tail(dat_raw$timestamp, n = 1)


# Fills in missing timestamps and flags "M" for missing and "N" for not qaqc'd:
raw_times <- tidyr::tibble(timestamp = seq(from = raw_start, to = raw_end,
                                    by = "15 min"))

unmatched_timestamp <- anti_join(raw_times, dat_raw, by = "timestamp")

dat_raw_times <- dat_raw %>%
  dplyr::full_join(raw_times, by = "timestamp") %>%
  dplyr::arrange(timestamp) %>%
  dplyr::group_by(timestamp) %>%
  dplyr::mutate(
    duplicate = n() > 1,
    wtmp_flag = "N") %>%
  dplyr::ungroup() %>%
  mutate(across(c(station_code, logger_serial, utc_offset, data_id), 
                ~ if_else(is.na(.x), first(na.omit(.x)), .x))) %>%
  dplyr::mutate(
    wtmp_flag = dplyr::case_when(
      is.na(wtmp) & wtmp_flag == "N" ~ "M",
      duplicate == TRUE & wtmp_flag == "N" ~ "D",
      wtmp_flag == "N" & timestamp > datetime_in ~ "V", 
      TRUE ~ wtmp_flag))

# Run QAQC Flags: ---------------------------------------------------------
# Compute statistics:
dat_stats <- dat_raw_times %>%
  dplyr::mutate(year = lubridate::year(timestamp),
                month = lubridate::month(timestamp),
                day = lubridate::day(timestamp)) %>% 
  dplyr::group_by(year, month, day) %>% 
  dplyr::mutate(daily_mean = mean(wtmp, na.rm = TRUE)) %>% 
  dplyr::ungroup() %>% 
  dplyr::mutate(t_change = abs(wtmp-lag(wtmp)),
                t_change = replace_na(t_change, 0),
                t_change_lead = abs(lead(wtmp) - wtmp),
                diff = abs(c(0, diff(wtmp))),
                diff_right = abs(wtmp - (rollmean(wtmp, k=5, fill=NA, align = "right"))),
                diff_left = abs(wtmp - (rollmean(wtmp, k=5, fill=NA, align = "left"))),
                stdev_right = roll_sd(wtmp, n = 2, fill = NA, align = "right"),
                stdev_left = roll_sd(wtmp, n = 2, fill = NA, align = "left")) %>%
  #rmean1 = rollmean(temp,k = 72, align = "left", fill = NA),
  #rmean2 = rollmean(lead(temp, 72), k = 72, align = "left", fill = NA)) %>%
  ungroup()

# Flag data:
dat_raw_qaqc <- dat_stats %>% 
  dplyr::mutate(wtmp_flag = case_when(t_change >= 0.8 ~ "S",
                               t_change_lead >= 0.8 ~ "S",
                               diff_right >= 1.5 ~ "S",
                               diff_left >= 1.5 ~ "S",
                               stdev_right >= 2 ~ "S",
                               stdev_left >= 2 ~ "S",
                               !between(wtmp, -20, 50) ~ "E",
                               wtmp >= 35 ~ "T",
                               wtmp < 0.0 ~ "B",
                               wtmp_flag == "M" ~ "M",
                               wtmp_flag == "V" ~ "V",
                               TRUE ~ "P"),
                qaqc_flag = NULL) %>%
  dplyr::reframe(data_id, station_code, timestamp, utc_offset, logger_serial,
                 wtmp, wtmp_flag)

# Data Visualization ------------------------------------------------------
plot_qaqc <- ggplot2::ggplot(dat_raw_qaqc, aes(x = timestamp, y = wtmp)) +
  ggplot2::geom_line() +
  ggplot2::geom_point(aes(color = wtmp_flag)) +
  ggplot2::geom_vline(data = subset(dat_raw_qaqc, wtmp_flag == "M"),
                      aes(xintercept = timestamp), color = "dark red") +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = unique(na.omit(dat_raw_qaqc$station_code))) +
  ggplot2::theme_bw() +
  ggplot2::scale_color_manual(values = c("P" = "green", #Pass
                                         "N" = "black", #No QAQC; default qaqc value; - !!!Send Report to Data Manager!!!
                                         "B" = "blue", #Below Ice
                                         "S" = "red", #Spike; likely de-watered
                                         "E" = "purple", #Outside equipment operating range
                                         "T" = "orange", #Above 35 degree threshold
                                         "D" = "Brown", #Duplicated timestamp - !!!Send Report to Data Manager!!!
                                         "V" = "pink", # Site visit
                                         "M" = "dark red")) # Missing values; likely due to dead battery


print(plot_qaqc) #Does not flag missing values at site visits

# Compile all data: -------------------------------------------------------
#####STOP!!!
#!!!Use this code if first record of series:
dat_raw_review <- dat_raw_qaqc

plot_review <- ggplot2::ggplot(dat_raw_review, aes(x = timestamp, y = wtmp)) +
  ggplot2::geom_line() +
  ggplot2::geom_point(aes(color = wtmp_flag)) +
  ggplot2::geom_vline(data = subset(dat_raw_review, wtmp_flag == "M"),
                      aes(xintercept = timestamp), color = "dark red") +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = unique(na.omit(dat_raw_review$station_code))) +
  ggplot2::theme_bw() +
  ggplot2::scale_color_manual(values = c("P" = "green", #Pass
                                         "N" = "black", #No QAQC; default qaqc value; - !!!Send Report to Data Manager!!!
                                         "B" = "blue", #Below Ice
                                         "S" = "red", #Spike; likely de-watered
                                         "E" = "purple", #Outside equipment operating range
                                         "T" = "orange", #Above 35 degree threshold
                                         "D" = "Brown", #Duplicated timestamp - !!!Send Report to Data Manager!!!
                                         "V" = "pink", # Site visit
                                         "M" = "dark red")) # Missing values; likely due to dead battery


plot(plot_review)

#####END OF FIRST SERIES CODE

#!!!Use this if there are preceding data sets
dat_comp <- rbind(dat_historical, dat_raw_qaqc) %>%
  dplyr::mutate(
    wtmp_flag = ifelse(
      timestamp >= prev_datetime_in & timestamp <=
        prev_datetime_out & wtmp_flag != "M", "V", wtmp_flag))

plot_comp <- ggplot2::ggplot(dat_comp, aes(x = timestamp, y = wtmp)) +
  ggplot2::geom_line() +
  ggplot2::geom_point(aes(color = wtmp_flag)) +
  ggplot2::geom_vline(data = subset(dat_comp, wtmp_flag == "M"),
                      aes(xintercept = timestamp), color = "dark red") +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = unique(na.omit(dat_comp$station_code))) +
  ggplot2::theme_bw() +
  ggplot2::scale_color_manual(values = c("P" = "green", #Pass
                                         "N" = "black", #No QAQC; default qaqc value; - !!!Send Report to Data Manager!!!
                                         "B" = "blue", #Below Ice
                                         "S" = "red", #Spike; likely de-watered
                                         "E" = "purple", #Outside equipment operating range
                                         "T" = "orange", #Above 35 degree threshold
                                         "D" = "Brown", #Duplicated timestamp - !!!Send Report to Data Manager!!!
                                         "V" = "pink", # Site visit
                                         "M" = "dark red")) # Missing values; likely due to dead battery

print(plot_comp)

# Prepare data output: ----------------------------------------------------
dat_raw_review <- dat_comp %>%
  dplyr::filter(dplyr::between(timestamp, raw_start, raw_end))

plot_review <- ggplot2::ggplot(dat_raw_review, aes(x = timestamp, y = wtmp)) +
  ggplot2::geom_line() +
  ggplot2::geom_point(aes(color = wtmp_flag)) +
  ggplot2::geom_vline(data = subset(dat_raw_review, wtmp_flag == "M"),
                      aes(xintercept = timestamp), color = "dark red") +
  ggplot2::labs(x = "Timestamp", y = "Water Temperature",
                title = "Water Temperature QAQC",
                subtitle = unique(na.omit(dat_raw_review$station_code))) +
  ggplot2::theme_bw() +
  ggplot2::scale_color_manual(values = c("P" = "green", #Pass
                                         "N" = "black", #No QAQC; default qaqc value; - !!!Send Report to Data Manager!!!
                                         "B" = "blue", #Below Ice
                                         "S" = "red", #Spike; likely de-watered
                                         "E" = "purple", #Outside equipment operating range
                                         "T" = "orange", #Above 35 degree threshold
                                         "D" = "Brown", #Duplicated timestamp - !!!Send Report to Data Manager!!!
                                         "V" = "pink", # Site visit
                                         "M" = "dark red")) # Missing values; likely due to dead battery
plot(plot_review)

####
#END
####

