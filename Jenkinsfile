pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "email-app"
        BACKEND_CONTAINER = "email-backend"
        FRONTEND_CONTAINER = "frontend-app"
        PATH = "/usr/local/bin:${env.PATH}"
    }

    stages {

        stage('Checkout Code') {
            steps {
                echo '📥 Checking out source code'
                checkout scm
            }
        }

        stage('Verify Docker & Compose') {
            steps {
                sh 'docker --version'
                sh 'docker-compose --version'
            }
        }

        stage('Clean Existing Containers') {
            steps {
                echo '🧹 Removing existing containers if present'
                sh '''
                    docker rm -f ${BACKEND_CONTAINER} || true
                    docker rm -f ${FRONTEND_CONTAINER} || true
                '''
            }
        }

        stage('Build Images') {
            steps {
                echo '🐳 Building Docker images using docker-compose'
                sh 'docker-compose build'
            }
        }

        stage('Run Containers') {
            steps {
                echo '🚀 Starting application containers'
                sh 'docker-compose up -d'
            }
        }

        stage('Wait for Backend') {
            steps {
                echo '⏳ Waiting for backend to be ready'
                retry(5) {
                    sleep 5
                    sh '''
                        docker exec ${BACKEND_CONTAINER} \
                        curl -f http://localhost:5000 || exit 1
                    '''
                }
            }
        }

        stage('Test Services') {
            steps {
                echo '🧪 Testing Backend API'
                sh 'curl --fail http://localhost:5000'

                echo '🧪 Testing Frontend UI'
                sh 'curl --fail http://localhost'
            }
        }
    }

    post {
        always {
            echo '🧽 Cleaning up stopped containers and networks'
            sh 'docker container prune -f || true'
            sh 'docker network prune -f || true'
        }
        success {
            echo '✅ Frontend & Backend deployed and tested successfully'
        }
        failure {
            echo '❌ Pipeline failed – check logs'
        }
    }
}
