
# Recommended Tech Stack for fipro

This document proposes a technology stack for building out the `fipro` project, moving it from a collection of scripts to a robust, scalable application.

## 1. Core Processing & Pipeline

The existing Python scripts are a good foundation. To make them more robust, I recommend standardizing on the following libraries:

*   **PDF Text Extraction:**
    *   **Primary:** **`PyMuPDF (fitz)`** or **`pdfplumber`**. Both are excellent for extracting text and table data from complex PDFs. `pdfplumber` is often more user-friendly for table extraction, which is common in bank statements.
*   **Data Manipulation:**
    *   **Primary:** **`pandas`**. This is the industry standard for handling tabular data in Python. All transaction data should be loaded into pandas DataFrames for cleaning, transformation, and analysis.
*   **Configuration:**
    *   **Primary:** **YAML files (`PyYAML` library)** for storing configuration like file paths, bank-specific parsing rules, and database credentials. This is cleaner than hardcoding values in scripts.
*   **Orchestration:**
    *   **Initial:** Simple shell scripts triggered by **`cron`** jobs for scheduled, automatic execution of the pipeline.
    *   **Future:** If the pipeline becomes more complex (e.g., multiple dependent steps, retries), consider a lightweight orchestrator like **`Prefect`**.

## 2. Database

Storing data in flat files (CSVs) is good for initial development but not for a real application. A database is essential for querying, analysis, and scalability.

*   **Initial/Development:**
    *   **Primary:** **`SQLite`**. It's a serverless, file-based database that's built into Python. It's perfect for getting started without any setup overhead.
*   **Production/Scalability:**
    *   **Primary:** **`PostgreSQL`**. It's a powerful, open-source, and highly reliable relational database that can handle large volumes of data and complex queries.
*   **ORM (Object-Relational Mapper):**
    *   **Primary:** **`SQLAlchemy`**. It's the most widely used ORM in the Python ecosystem and integrates perfectly with pandas and web frameworks like FastAPI or Flask. It allows you to interact with your database using Python objects instead of writing raw SQL.

## 3. API / Backend

To serve the processed data to a web frontend, you'll need a backend API.

*   **Framework:**
    *   **Primary:** **`FastAPI`**. It is a modern, high-performance Python web framework that is extremely easy to learn. It comes with automatic interactive documentation (Swagger UI), which is invaluable for development and testing.
    *   **Alternative:** **`Flask`**. A classic, lightweight, and flexible framework. A very solid choice as well.

## 4. Frontend (Web UI)

For the user-facing application to view and categorize transactions.

*   **JavaScript Framework:**
    *   **Primary:** **`React`** (with TypeScript). It is the most popular frontend library with a massive ecosystem. Using TypeScript adds static typing, which helps catch errors early and improves code quality.
    *   **Alternative:** **`Vue.js`**. Often considered to have a gentler learning curve than React.
*   **UI Component Library:**
    *   **Primary:** **`MUI (Material-UI)`** or **`Ant Design`**. These libraries provide a set of pre-built, professional-looking React components (buttons, tables, modals) that will significantly speed up development.
*   **Data Visualization:**
    *   **Primary:** **`Recharts`** or **`Chart.js`**. These are easy-to-use charting libraries for React that can create interactive bar charts, line charts, and pie charts to visualize financial data.
*   **Styling:**
    *   **Primary:** **`Tailwind CSS`**. A utility-first CSS framework that allows for rapid and consistent styling without writing custom CSS.
