####
#Header
####

library(rmarkdown)

# Write Data and Save: ----------------------------------------------------
dat_raw_review$timestamp <- format(dat_raw_review$timestamp, "%Y-%m-%d %H:%M:%S",
                                 usetz = F)
write.csv(dat_raw_review,
          paste0(dat_dir, "/01_Data/02_Tidy/", station_code, "_tidy_",
                 logger_serial, "_",raw_fileDate, ".csv"), row.names = F)

# Render R Markdown Document:
rmarkdown::render(paste0(user_dir, "/06_Scripts/WT_ReportMarkdown.Rmd"),
                  output_dir = paste0(matching_folder, "/03_Reports/02_QAQC"),
                  output_file = paste0(station_code, "_qaqcReport_",
                                       logger_serial, "_", raw_fileDate))

####
#END
####

