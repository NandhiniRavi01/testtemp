pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "email-app"
        VM_USER    = "ubuntu"
        VM_HOST    = "65.1.129.37"
        VM_APP_DIR = "/home/ubuntu/email-main"
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {

        stage('Checkout Code') {
            steps {
                echo "📥 Checking out source code"
                checkout scm
            }
        }

        stage('Test SSH Connection') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ubuntu@65.1.129.37 << 'EOF'
                      echo "✅ SSH connected"
                      hostname
                      whoami
                      docker --version
                      docker compose version
                    EOF
                    '''
                }
            }
        }

        stage('Remove Old Code on VM') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ubuntu@65.1.129.37 << 'EOF'
                      echo "🧹 Removing old application code"
                      rm -rf /home/ubuntu/email-main
                      mkdir -p /home/ubuntu/email-main
                    EOF
                    '''
                }
            }
        }

        stage('Copy Fresh Code to VM') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh '''
                    rsync -avz \
                      --exclude='.git' \
                      --exclude='node_modules' \
                      --exclude='__pycache__' \
                      ./ ubuntu@65.1.129.37:/home/ubuntu/email-main/
                    '''
                }
            }
        }

        stage('Cleanup Containers & Images') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ubuntu@65.1.129.37 << 'EOF'
                      cd /home/ubuntu/email-main
                      echo "🧹 Stopping containers"
                      docker compose down --volumes --remove-orphans || true

                      echo "🧹 Removing unused images"
                      docker image prune -af || true
                    EOF
                    '''
                }
            }
        }

        stage('Build & Deploy') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ubuntu@65.1.129.37 << 'EOF'
                      set -e
                      cd /home/ubuntu/email-main

                      echo "🐳 Building fresh images"
                      docker compose build --no-cache

                      echo "🚀 Starting containers"
                      docker compose up -d

                      docker compose ps
                    EOF
                    '''
                }
            }
        }

        stage('Verify Services') {
            steps {
                sshagent(['aws-email-vm-ssh']) {
                    retry(5) {
                        sh '''
                        ssh -o StrictHostKeyChecking=no ubuntu@65.1.129.37 << 'EOF'
                          echo "🔍 Backend check"
                          curl -f http://localhost:5000

                          echo "🔍 Frontend check"
                          curl -f http://localhost
                        EOF
                        '''
                        sleep 5
                    }
                }
            }
        }
    }

    post {
        success {
            echo "✅ Deployment successful"
        }
        failure {
            echo "❌ Deployment failed — check Jenkins logs"
        }
    }
}
