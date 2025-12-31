pipeline {
    agent any

    environment {
        VM_USER    = "ubuntu"
        VM_HOST    = "54.80.134.161"
        VM_APP_DIR = "/home/ubuntu/email-main"
        GIT_REPO   = "https://github.com/NandhiniRavi01/testtemp.git"
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {

        // 1️⃣ Test SSH Connection
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

        // 2️⃣ Deploy Code on VM (Clone or Pull)
        stage('Deploy Code on VM') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        mkdir -p ${VM_APP_DIR}

                        # Clone or update repo
                        if [ -d ${VM_APP_DIR}/.git ]; then
                            cd ${VM_APP_DIR} && git reset --hard && git pull
                        else
                            git clone ${GIT_REPO} ${VM_APP_DIR}
                        fi
                    '
                    """
                }
            }
        }

        // 3️⃣ Verify Docker & Compose
        stage('Verify Docker & Compose on VM') {
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

        // 4️⃣ Build & Run Containers
        stage('Build & Run Docker Compose') {
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

        // 5️⃣ Wait for Backend
        stage('Wait for Backend') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    retry(5) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                            curl --fail --max-time 5 http://localhost:5000
                        '
                        """
                        sleep 5
                    }
                }
            }
        }

        // 6️⃣ Test Services
        stage('Test Services') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        echo "🔍 Backend test"
                        curl --fail --max-time 5 http://localhost:5000

                        echo "🔍 Frontend test"
                        curl --fail --max-time 5 http://localhost:80 || curl --fail --max-time 5 http://localhost:3000
                    '
                    """
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
            echo '✅ Deployment successful (Frontend + Backend Docker Compose)'
        }

        failure {
            echo '❌ Deployment failed – check logs'
        }
    }
}
