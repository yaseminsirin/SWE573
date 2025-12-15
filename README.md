# TimeBank (SWE573 Project)

**TimeBank** is a community-based service exchange platform where time is the currency. Users can offer their skills, request services, and trade hours within a trusted network. Built with Django and React.

## 🚀 Installation & Setup

You can run the project either locally using Python or via Docker.

### Option 1: Local Installation

Follow these steps to set up the project environment on your local machine.

**1. Clone the repository**
```bash
git clone [https://github.com/yaseminsirin/SWE573.git](https://github.com/yaseminsirin/SWE573.git)
cd SWE573
2. Create and activate a virtual environment (Recommended)
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Environment Configuration Create a .env file in the root directory of the project. You can copy the example configuration (if available) or create one manually:
# Example .env content
DEBUG=True
SECRET_KEY=your-secret-key-here
5. Apply Database Migrations Initialize the database tables:
python manage.py migrate
6. Run the Development Server Start the application:
python manage.py runserver
The application will be available at: http://127.0.0.1:8000
Option 2: Docker Installation (Fastest)

If you have Docker installed, you can spin up the entire application with a single command.

1. Build and Run Containers
docker-compose up --build
The application will be accessible at http://localhost:8000.
Technologies Used
Backend: Django, Django REST Framework

Database: PostgreSQL

Containerization: Docker

External APIs: Wikidata (for semantic tagging)
