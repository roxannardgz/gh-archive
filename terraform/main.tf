resource "google_storage_bucket" "gharchive_bucket" {
  name     = "${var.project_id}-bucket"
  location = var.region

  uniform_bucket_level_access = true
}

resource "google_bigquery_dataset" "gharchive_dataset" {
  dataset_id                 = "gharchive_dataset"
  location                   = var.region
  delete_contents_on_destroy = true
}