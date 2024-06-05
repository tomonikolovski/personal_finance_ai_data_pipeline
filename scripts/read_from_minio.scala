// Set MinIO credentials and endpoint
sc.hadoopConfiguration.set("fs.s3a.access.key", "minio")
sc.hadoopConfiguration.set("fs.s3a.secret.key", "minio123")
sc.hadoopConfiguration.set("fs.s3a.endpoint", "http://minio:9000")
sc.hadoopConfiguration.set("fs.s3a.connection.ssl.enabled", "false") // Set to true if using HTTPS
sc.hadoopConfiguration.set("fs.s3a.path.style.access", "true") // MinIO requires path style access

// Define the MinIO path
val minioPath = "s3a://bucket1/topic1/partition=0/"

// Import necessary classes
import org.apache.hadoop.fs.{FileSystem, Path}
import java.net.URI

// Use the Hadoop FileSystem API to list files
val fs = FileSystem.get(new URI(minioPath), sc.hadoopConfiguration)
val fileStatus = fs.listStatus(new Path(minioPath))

// Print the list of files
fileStatus.foreach(status => println(status.getPath))
