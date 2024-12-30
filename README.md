# LoginTracker
A work-in-progress Python/Google Sheets sign-in/sign-out system

Keep in mind: this is VERY work-in-progress. Expect stuff to be broken.

For a quick (but relatively controversial) way of installing everything but the service_account.json file:
* Flask: `curl -sSL https://github.com/faletto/LoginTracker/install.sh | bash`
* Tkinter: `curl -sSL https://github.com/faletto/LoginTracker/install_tkinter.sh | bash`

Small portions of the Python were done by ChatGPT. I (@TaigaM123) am not sure how much time or effort it saved though.

## Advanced
**Time Machine** is a feature that allows administrators to choose a custom timestamp to login/logout. It is disabled by default. To enable it, create a file called "time-machine" in the root directory of the project.

### Windows
`C:\path\to\LoginTracker> echo "" > time-machine`
### Not Windows
`/path/to/LoginTracker $ touch time-machine`