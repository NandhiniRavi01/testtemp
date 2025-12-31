pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "email-app"
        BACKEND_CONTAINER   = "email-backend"
        FRONTEND_CONTAINER  = "frontend-app"

        PATH = "/usr/local/bin:${env.PATH}"

        VM_USER = "ubuntu"
        VM_HOST = "3.81.14.177"
        APP_DIR = "~/email-main"
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }

    stages {

        /* ---------------------------------------------------------
         * 1. VERIFY VM CONNECTIVITY (MOST IMPORTANT STAGE)
         * --------------------------------------------------------- */
        stage('Test VM SSH Connection') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        echo "✅ SSH connection successful"
                        echo "Host:" && hostname
                        echo "User:" && whoami
                        echo "Uptime:" && uptime
                    '
                    """
                }
            }
        }

        /* ---------------------------------------------------------
         * 2. CHECKOUT CODE ON VM
         * --------------------------------------------------------- */
        stage('Checkout Code on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        mkdir -p ${APP_DIR}

                        if [ -d ${APP_DIR}/.git ]; then
                            cd ${APP_DIR}
                            git reset --hard
                            git pull origin main
                        else
                            git clone -b main https://github.com/NandhiniRavi01/test.git ${APP_DIR}
                        fi
                    '
                    """
                }
            }
        }

        /* ---------------------------------------------------------
         * 3. VERIFY DOCKER & COMPOSE
         * --------------------------------------------------------- */
        stage('Verify Docker & Compose on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        docker --version
                        docker compose version
                    '
                    """
                }
            }
        }

        /* ---------------------------------------------------------
         * 4. BUILD DOCKER IMAGES
         * --------------------------------------------------------- */
        stage('Build Images on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        cd ${APP_DIR}
                        docker compose build
                    '
                    """
                }
            }
        }

        /* ---------------------------------------------------------
         * 5. RUN CONTAINERS
         * --------------------------------------------------------- */
        stage('Run Containers on VM') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        cd ${APP_DIR}
                        docker compose up -d
                    '
                    """
                }
            }
        }

        /* ---------------------------------------------------------
         * 6. WAIT FOR BACKEND TO BE READY
         * --------------------------------------------------------- */
        stage('Wait for Backend') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    retry(5) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                            curl -f http://localhost:5000
                        '
                        """
                        sleep 5
                    }
                }
            }
        }

        /* ---------------------------------------------------------
         * 7. TEST FRONTEND & BACKEND
         * --------------------------------------------------------- */
        stage('Test Services') {
            steps {
                sshagent(['docker-vm-ssh']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                        echo "🔍 Testing backend..."
                        curl --fail http://localhost:5000

                        echo "🔍 Testing frontend..."
                        curl --fail http://localhost
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
            sshagent(['docker-vm-ssh']) {
                sh """
                ssh -o StrictHostKeyChecking=no ${VM_USER}@${VM_HOST} '
                    docker system prune -af || true
                '
                """
            }
        }

        success {
            echo '✅ Frontend & Backend successfully deployed and verified on VM'
        }

        failure {
            echo '❌ Pipeline failed – please check Jenkins logs'
        }
    }
}
