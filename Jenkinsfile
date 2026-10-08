pipeline {
    agent any

    environment {
        APP_NAME     = 'aceest-fitness'
        IMAGE_NAME   = "aceest-fitness:${BUILD_NUMBER}"
        CONTAINER_PORT = 5000
        HOST_PORT      = 5000
    }

    stages {
        stage('Stage 1: Checkout SCM') {
            steps {
                echo '=== Pulling latest codebase from repository ==='
                checkout scm
            }
        }

        stage('Stage 2: Environment Setup & Linting') {
            steps {
                echo '=== Setting up virtual environment & running Flake8 linter ==='
                sh '''
                    python3 -m venv .venv || true
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    flake8 . --count --show-source --statistics
                '''
            }
        }

        stage('Stage 3: Automated Pytest Quality Gate') {
            steps {
                echo '=== Executing Pytest test suite with code coverage ==='
                sh '''
                    . .venv/bin/activate
                    pytest --cov=app --cov-report=term-missing --junitxml=reports/test-results.xml tests/
                '''
            }
            post {
                always {
                    junit testResults: 'reports/test-results.xml', allowEmptyResults: true
                }
            }
        }

        stage('Stage 4: Docker Image Assembly') {
            steps {
                echo "=== Building production Docker image: ${IMAGE_NAME} ==="
                sh """
                    docker build -t ${IMAGE_NAME} -t ${APP_NAME}:latest .
                """
            }
        }

        stage('Stage 5: Containerized Smoke Test') {
            steps {
                echo '=== Running Pytest inside newly built container image ==='
                sh """
                    docker run --rm ${APP_NAME}:latest pytest tests/
                """
            }
        }

        stage('Stage 6: Deploy to Local Runtime') {
            steps {
                echo '=== Refreshing local live container deployment ==='
                sh """
                    docker stop ${APP_NAME}-live || true
                    docker rm ${APP_NAME}-live || true
                    docker run -d --name ${APP_NAME}-live -p ${HOST_PORT}:${CONTAINER_PORT} ${APP_NAME}:latest
                    sleep 3
                    docker ps | grep ${APP_NAME}-live
                """
            }
        }
    }

    post {
        success {
            echo '=== Jenkins Pipeline BUILD SUCCESSFUL: Quality gates passed and container deployed! ==='
        }
        failure {
            echo '=== Jenkins Pipeline BUILD FAILED: Review console output for debugging ==='
        }
        always {
            cleanWs(cleanWhenNotBuilt: false,
                    deleteDirs: true,
                    notFailBuild: true,
                    patterns: [[pattern: '.venv/**', type: 'INCLUDE']])
        }
    }
}
