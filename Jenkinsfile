pipeline {
    agent any

    environment {
          // Remote Docker host
        DOCKER_HOST = "tcp://3.81.14.177:2375"
        DOCKER_BUILDKIT = "1"
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
                sh 'docker compose version'
            }
        }

        stage('Build Images') {
            steps {
                dir('email-main') {
                    echo '🐳 Building Docker images using docker compose'
                    sh 'docker compose build'
                }
            }
        }

        stage('Run Containers') {
            steps {
                dir('email-main') {
                    echo '🚀 Starting application containers'
                    sh 'docker compose up -d'
                }
            }
        }

        stage('Wait for Backend') {
            steps {
                echo '⏳ Waiting for backend to be ready'
                retry(5) {
                    sleep 5
                    // Host-based curl test (requires backend port 5000 mapped to host)
                    sh 'curl -f http://localhost:5000 || exit 1'
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

        // Cleanup stage removed to keep containers running after pipeline
        // stage('Cleanup Containers') {
        //     steps {
        //         dir('email-main') {
        //             echo '🧹 Stopping containers'
        //             sh 'docker compose down'
        //         }
        //     }
        // }
    }

    post {
        always {
            echo '🧽 Pruning unused Docker resources (images & cache only)'
            sh 'docker system prune -af || true'
        }
        success {
            echo '✅ Frontend & Backend deployed and tested successfully'
        }
        failure {
            echo '❌ Pipeline failed – check logs'
        }
    }
}
