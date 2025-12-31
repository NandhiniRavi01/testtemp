pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "email-app"
        BACKEND_CONTAINER = "email-backend"
        FRONTEND_CONTAINER = "frontend-app"
        PATH = "/usr/local/bin:${env.PATH}"
        VM_USER = "ubuntu"
        VM_HOST = "3.81.14.177"
        APP_DIR = "~/email-main"
    }

    stages {

        stage('Checkout Code on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        mkdir -p ${APP_DIR} &&
                        if [ -d ${APP_DIR}/.git ]; then
                            cd ${APP_DIR} && git pull
                        else
                            git clone -b main https://github.com/NandhiniRavi01/test.git ${APP_DIR}
                        fi
                    '
                    """
                }
            }
        }

        stage('Verify Docker & Compose on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'docker --version && docker compose version'"
                }
            }
        }

        stage('Build Images on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'cd ${APP_DIR} && docker compose build'"
                }
            }
        }

        stage('Run Containers on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'cd ${APP_DIR} && docker compose up -d'"
                }
            }
        }

        stage('Wait for Backend') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    retry(5) {
                        sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'curl -f http://${VM_HOST}:5000 || exit 1'"
                        sleep 5
                    }
                }
            }
        }

        stage('Test Services') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'curl --fail http://${VM_HOST}:5000'"
                    sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'curl --fail http://${VM_HOST}'"
                }
            }
        }
    }

    post {
        always {
            sshagent(['docker-vm-ssh']) {
                sh "ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} 'docker system prune -af || true'"
            }
        }
        success {
            echo '✅ Frontend & Backend deployed and tested successfully on VM'
        }
        failure {
            echo '❌ Pipeline failed – check logs'
        }
    }
}
