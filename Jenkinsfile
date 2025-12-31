pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "email-app"
        BACKEND_CONTAINER   = "email-backend"
        FRONTEND_CONTAINER  = "frontend-app"

        PATH = "/usr/local/bin:${env.PATH}"

        VM_USER = "ubuntu"
        VM_HOST = "54.80.134.161"
        VM_APP_DIR = "/home/ubuntu/email-main"
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }

    stages {

        // 1️⃣ Checkout Code
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        // 2️⃣ Test SSH Connection
        stage('Test VM SSH Connection') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        echo "✅ SSH Connection OK"
                        hostname
                        whoami
                        uptime
                    '
                    """
                }
            }
        }

        // 3️⃣ Copy Code to VM
        stage('Copy Code to VM') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    rsync -avz --delete \
                        --exclude='.git' \
                        --exclude='node_modules' \
                        --exclude='__pycache__' \
                        ./ ${VM_USER}@${VM_HOST}:${VM_APP_DIR}/
                    """
                }
            }
        }

        // 4️⃣ Verify Docker & Compose
        stage('Verify Docker & Compose') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        docker --version
                        docker compose version || docker-compose --version
                    '
                    """
                }
            }
        }

        // 5️⃣ Build & Run Containers
        stage('Build & Run Containers') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        cd ${VM_APP_DIR}
                        docker compose build
                        docker compose up -d
                    '
                    """
                }
            }
        }

        // 6️⃣ Wait for Backend
        stage('Wait for Backend') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    retry(5) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                            curl --fail --max-time 5 http://${VM_HOST}:5000
                        '
                        """
                        sleep 5
                    }
                }
            }
        }

        // 7️⃣ Test Services in Parallel
        stage('Test Services') {
            parallel {
                stage('Backend Test') {
                    steps {
                        sshagent(['aws-email-vm-ssh']) {
                            sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'curl --fail --max-time 5 http://${VM_HOST}:5000'"
                        }
                    }
                }
                stage('Frontend Test') {
                    steps {
                        sshagent(['aws-email-vm-ssh']) {
                            sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'curl --fail --max-time 5 http://${VM_HOST}'"
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            sshagent(['aws-email-vm-ssh']) {
                sh """
                ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                    docker system prune -af || true
                '
                """
            }
        }

        success {
            echo '✅ Deployment successful (Jenkins → VM)'
        }

        failure {
            echo '❌ Deployment failed – check logs'
        }
    }
}
