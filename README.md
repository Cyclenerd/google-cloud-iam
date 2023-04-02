# Google Cloud Identity and Access Management (IAM)

[![Bagde: Google Cloud](https://img.shields.io/badge/Google%20Cloud-%234285F4.svg?logo=google-cloud&logoColor=white)](#readme)
[![Bagde: CI](https://github.com/Cyclenerd/google-cloud-iam/actions/workflows/build.yml/badge.svg)](https://github.com/Cyclenerd/google-cloud-iam/actions/workflows/build.yml)
[![Bagde: GitHub](https://img.shields.io/github/license/cyclenerd/google-cloud-iam)](https://github.com/Cyclenerd/google-cloud-iam/blob/master/LICENSE)

This webapp lists predefined roles and permissions for Google Cloud Platform Identity and Access Management (IAM).

I built it so that I can quickly search for permissions and identify the associated role.
The official [Google Documentation](https://cloud.google.com/iam/docs/understanding-roles) is too slow and messy for me.

[![Screenshot](./img/screenshot.png)](https://gcloud-iam.nkn-it.de/permissions.html)

## 🧑‍💻 Development

If you want to customize or run the webapp on your [Gitpod](https://gitpod.io/#https://github.com/Cyclenerd/google-cloud-iam) or local computer,
you need the following requirements.

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/Cyclenerd/google-cloud-iam)

### Requirements

* [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
* JSON processor (`jq`)
* Perl 5 (`perl`)
* Perl modules:
	* [JSON::XS](https://metacpan.org/pod/JSON::XS)
	* [Template::Toolkit](https://metacpan.org/pod/Template::Toolkit)
	* [plackup](https://metacpan.org/dist/Plack/view/script/plackup)

<details>
<summary><b>Debian/Ubuntu</b></summary>

Packages:
```shell
sudo apt update
sudo apt install \
	libjson-xs-perl \
	libtemplate-perl \
	libplack-perl \
	jq
```

[Google Cloud CLI](https://cloud.google.com/sdk/docs/install#deb):
```shell
sudo apt-get install apt-transport-https ca-certificates gnupg
# Add the gcloud CLI distribution URI as a package source
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud public key.
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.gpg
# Update and install the gcloud CLI
sudo apt-get update
sudo apt-get install google-cloud-cli
```
</details>

<details>
<summary><b>macOS</b></summary>

Homebrew packages:
```shell
brew install perl
brew install cpanminus pkg-config
brew install --cask google-cloud-sdk
brew install jq
```

Perl modules:
```shell
cpanm --installdeps .
```
</details>

Build:
```shell
cd build
bash roles.sh
bash permissions.sh
perl build.pl
```

Run:
```shell
plackup --host 127.0.0.1
```

## ❤️ Contributing

Have a patch that will benefit this project?
Awesome! Follow these steps to have it accepted.

1. Please read [how to contribute](CONTRIBUTING.md).
1. Fork this Git repository and make your changes.
1. Create a Pull Request.
1. Incorporate review feedback to your changes.
1. Accepted!


## 📜 License

All files in this repository are under the [Apache License, Version 2.0](LICENSE) unless noted otherwise.

Portions of this webapp are modifications based on work created and shared by [Google](https://developers.google.com/readme/policies)
and used according to terms described in the [Creative Commons 4.0 Attribution License](https://creativecommons.org/licenses/by/4.0/).