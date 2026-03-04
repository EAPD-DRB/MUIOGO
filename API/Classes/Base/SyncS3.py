"""AWS S3 synchronisation helpers.

Provides upload, download, and delete operations for syncing local
case data with an S3 bucket.
"""

import boto3
import os
import glob
from pathlib import Path
from collections.abc import Iterable
from typing import List, Optional

# from Classes.Base.S3 import S3
from Classes.Base import Config


class SyncS3():
    """Client for synchronising local case data with AWS S3.

    Attributes:
        resource: ``boto3`` S3 resource handle.
        client: ``boto3`` S3 low-level client handle.
    """

    def __init__(self) -> None:
        """Initialise S3 resource and client using application config."""
        #S3.__init__(self)
        self.resource = boto3.resource(
        "s3",
        aws_access_key_id=Config.S3_KEY,
        aws_secret_access_key=Config.S3_SECRET
        )

        self.client = boto3.client(
            's3',
            aws_access_key_id=Config.S3_KEY,
            aws_secret_access_key=Config.S3_SECRET
        )

    def getCasesSyncInit(self) -> List[str]:
        """List case prefixes (top-level folders) in the S3 bucket.

        Returns:
            List of case name strings found in the bucket.

        Raises:
            IOError: If the bucket cannot be accessed.
        """
        try:
            my_bucket = self.resource.Bucket(Config.S3_BUCKET)
            result = my_bucket.meta.client.list_objects(Bucket=my_bucket.name, Delimiter='/')
            if isinstance(result.get('CommonPrefixes'), Iterable):
                cases = [ f.get('Prefix')[:-1] for f in result.get('CommonPrefixes')]
            else:
                cases = []
            return cases
        except(IOError):
            raise IOError

    def downloadSync(self, prefix: str, local: Path, bucket: str) -> None:
        """Download all objects matching *prefix* from S3 to a local path.

        Args:
            prefix: S3 key prefix to match (typically the case name).
            local: Local directory to place downloaded files in.
            bucket: Name of the S3 bucket.

        Raises:
            IOError: If an I/O error occurs during download.
        """
        client=self.client
        keys = []
        dirs = []
        next_token = ''
        base_kwargs = {
            'Bucket':bucket,
            'Prefix':prefix,
        }
        while next_token is not None:
            kwargs = base_kwargs.copy()
            if next_token != '':
                kwargs.update({'ContinuationToken': next_token})
            results = client.list_objects_v2(**kwargs)
            contents = results.get('Contents')
            if contents:
                for i in contents:
                    k = i.get('Key')
                    if k[-1] != '/':
                        keys.append(k)
                    else:
                        dirs.append(k)
            next_token = results.get('NextContinuationToken')
        for d in dirs:
            dest_pathname = os.path.join(local, d)
            if not os.path.exists(os.path.dirname(dest_pathname)):
                os.makedirs(os.path.dirname(dest_pathname))
        for k in keys:
            dest_pathname = os.path.join(local, k)
            if not os.path.exists(os.path.dirname(dest_pathname)):
                os.makedirs(os.path.dirname(dest_pathname))
            client.download_file(bucket, k, dest_pathname)

    #s3.uploadSync(localDir, case, Config.S3_BUCKET, '*')
    def uploadSync(
        self,
        localDir: Path,
        awsInitDir: str,
        bucketName: str,
        tag: str,
        prefix: str = os.sep,
    ) -> None:
        """Upload a local directory tree to an S3 bucket.

        Args:
            localDir: Local directory to be uploaded.
            awsInitDir: Prefix 'directory' in AWS.
            bucketName: Target S3 bucket name.
            tag: Glob pattern to select files (e.g. ``'*'``, ``'*png'``).
            prefix: Leading string to strip from local file paths
                (defaults to :data:`os.sep`).
        """
        resource = self.resource
        # mydirs daje listu svvih file i folder u localDir npr WebApp/DataStorage/Demo/genData.json
        mydirs = list(localDir.glob('**'))
        for mydir in mydirs:
            dirNames = glob.glob(os.path.join(mydir, tag))
            fileNames = [f for f in dirNames if not Path(f).is_dir()]
            #rows = len(fileNames)
            for i, FullfileName in enumerate(fileNames):
                #dobijemo ime file npr, genData.json
                fileName = str(FullfileName).replace(str(localDir), '')
                if fileName.startswith(prefix):  # only modify the text if it starts with the prefix
                    fileName = fileName.replace(prefix, "", 1) # remove one instance of prefix
                    fileName = fileName.replace(os.sep, '/')

                awsPath = str(awsInitDir) + '/' + str(fileName)
                resource.meta.client.upload_file(FullfileName, bucketName, awsPath)

    def deleteSync(self, case: str) -> None:
        """Delete all objects for a case from the S3 bucket.

        Args:
            case: The case name whose S3 objects should be removed.

        Raises:
            IOError: If the deletion fails.
        """
        try:
            my_bucket = self.resource.Bucket(Config.S3_BUCKET)
            my_bucket.objects.filter(Prefix=case+"/").delete()
        except(IOError):
            raise IOError

    def updateSync(self, localFile: Path, awsInitDir: str, bucketName: str) -> None:
        """Upload a single local file to an S3 bucket.

        Args:
            localFile: Path to the local file to upload.
            awsInitDir: Prefix 'directory' in AWS.
            bucketName: Target S3 bucket name.
        """
        resource = self.resource
        fileName = localFile.name
        localFileStr: str = str(localFile).replace(os.sep, '/')
        if awsInitDir != '':
            awsPath = str(awsInitDir) + '/' + str(fileName)
        else:
            awsPath = str(fileName)
        resource.meta.client.upload_file(localFileStr, bucketName, awsPath)