# TG Tools - Telegram Automation Suite

## 1. Project Overview

TG Tools is a powerful, containerized application designed to automate various tasks on Telegram. It provides a user-friendly web interface to manage multiple Telegram accounts and run background jobs for promotion, monitoring, and direct messaging.

The application consists of:
- **FastAPI Backend:** Manages accounts, jobs, and the API.
- **React Frontend:** A web-based user interface for interacting with the application.
- **Celery Workers:** Handle the execution of long-running background jobs.
- **PostgreSQL Database:** Stores all application data, including accounts and job history.
- **Redis:** Acts as the message broker for Celery.

---

## 2. Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Docker:** [Get Docker](https://docs.docker.com/get-docker/)
- **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop).

---

## 3. Setup and Installation

Getting the application running is simple. Follow these steps:

**Step 1: Get the Latest Code**
Make sure your local code is up to date with the latest version from the repository. If you have made local changes, it's best to reset them to the final version. You can do this with the following commands:
```bash
git fetch origin
git reset --hard origin/main
```

**Step 2: Start the Application**
Navigate to the root directory of the project in your terminal and run the following command:

```bash
docker compose up --build -d
```

- `up`: Creates and starts all the services defined in `docker-compose.yml`.
- `--build`: Builds the images from the Dockerfiles the first time you run it, or if any code has changed.
- `-d`: Runs the containers in "detached" mode, meaning they run in the background.

The first time you run this, it may take a few minutes to download the base images and build the application.

**Step 3: Access the Application**
Once all services are running, you can access the web interface by navigating to the following URL in your web browser:

**http://localhost:3000**

---

## 4. How to Use the Application

### 4.1. Adding and Verifying a Telegram Account

For most services to work, you first need to add a Telegram account to the system. This is a **one-time setup** for each account to authorize the application.

1.  **Navigate to the "Accounts" Page:** In the web UI, go to the Accounts section.
2.  **Create a New Account:** Click the button to add a new account. You will need to provide:
    *   A **Nickname** for the account.
    *   Your **Phone Number** (in international format, e.g., `+15551234567`).
    *   Your **API ID** and **API Hash** (you can get these from [my.telegram.org](https://my.telegram.org)).
3.  **Send Verification Code:** After creating the account, you will see it in the list with a "pending_verification" status. You will need to trigger the verification process, which will send a login code to your Telegram app.
4.  **Verify the Code:** Once you receive the code on your Telegram app, enter it into the UI to complete the verification.

Once verified, the account status will change to **"active"**, and a secure `.session` file will be created for it. This account can now be used to run jobs.

### 4.2. Running Jobs

Navigate to the specific service you want to use (e.g., "Auto Promo", "Mass DM").

1.  **Select the Account:** Choose one of your active, verified accounts from the dropdown list.
2.  **Fill in the Job Details:** Enter the required information, such as target groups, messages, or CSV files.
3.  **Create the Job:** Click the "Create Job" button.

You can monitor the status of your jobs on the "Jobs" page. The status will change from `pending` -> `running` -> `completed` (or `failed`).

---

## 5. Service-Specific Instructions & CSV Formats

Some services require you to upload a CSV file. The format of this file is very important.

### 5.1. Mass DM (via Account)

This service sends direct messages to a list of users from one of your authenticated accounts.

-   **CSV Format:** The CSV file must contain a header row with at least one of the following columns:
    -   `user_id`: The numerical user ID of the recipient.
    -   `username`: The `@username` of the recipient.

    **Example `users.csv`:**
    ```csv
    username,user_id
    some_user,
    ,123456789
    another_user,987654321
    ```

### 5.2. Mass DM (via Bot)

This service sends direct messages to a list of users or groups from a Telegram Bot that you own.

-   **CSV Format:** The CSV file **must** contain a header row with a column named `chat_id`.
    -   `chat_id`: This can be a user's numerical ID, a group's numerical ID (e.g., `-100123456...`), or a public channel/user's username (e.g., `@some_channel`).

    **Example `bot_dms.csv`:**
    ```csv
    chat_id
    -100123456789
    123456789
    some_username
    ```

### 5.3. Group Monitor

This service monitors groups for keywords and generates a CSV report. You do not need to upload a CSV for this service.

-   **Output:** When the job is `completed`, a "Download CSV" button will appear on the "Jobs" page, allowing you to download the results.

---

## 6. Troubleshooting

-   **Job fails immediately:** If a job fails right away, check the "Error Message" column on the Jobs page. The most common reason is that the account used for the job is not authenticated. Make sure you have completed the verification process for the account.
-   **Containers are not starting:** Use the command `docker compose logs` to see the logs for all services. If a service is crashing, the logs will usually tell you why.
-   **"Database is locked" error in logs:** This was a bug in older versions. If you see this, ensure you have the latest code and have run `docker compose up --build` to rebuild your images.
