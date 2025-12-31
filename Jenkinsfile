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

        /* ---------------------------------------------------------
         * 1. CHECKOUT CODE IN JENKINS (FROM GITHUB)
         * --------------------------------------------------------- */
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        /* ---------------------------------------------------------
         * 2. VERIFY VM SSH CONNECTIVITY
         * --------------------------------------------------------- */
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

        /* ---------------------------------------------------------
         * 3. COPY CODE FROM JENKINS → VM
         * --------------------------------------------------------- */
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

        /* ---------------------------------------------------------
         * 4. VERIFY DOCKER & COMPOSE ON VM
         * --------------------------------------------------------- */
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

        /* ---------------------------------------------------------
         * 5. BUILD & RUN DOCKER IMAGES
         * --------------------------------------------------------- */
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

        /* ---------------------------------------------------------
         * 6. WAIT FOR BACKEND
         * --------------------------------------------------------- */
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

        /* ---------------------------------------------------------
         * 7. TEST SERVICES
         * --------------------------------------------------------- */
        stage('Test Services') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        echo "🔍 Backend test"
                        curl --fail --max-time 5 http://${VM_HOST}:5000

                        echo "🔍 Frontend test"
                        curl --fail --max-time 5 http://${VM_HOST}
                    '
                    """
                }
            }
        }
    }

    /* -------------------------------------------------------------
     * POST ACTIONS
     * ------------------------------------------------------------- */
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
