def APP_NAME = "githubassistant"
def slackResponse = slackSend(channel: "datasci-devops", message: "STARTED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")

pipeline {
  options {
    timestamps()
  }
  agent {
        kubernetes {
            cloud "rke-executors"
            yamlFile "jenkins-agent-pod.yaml"
        }
  }
  environment {
    JENKINS_GIT_CREDS = credentials('jenkins-svc-to-bvhub01')
  }

  
stages {
stage('SonarQube analysis') {
          environment {
            scannerHome = tool 'SonarQube-Scanner';
          }
          steps {
            withSonarQubeEnv('SonarQube') { 
              sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectKey=githubassistant -Dsonar.sources=."
            }
          }
          post {
            success {
              slackSend(channel: slackResponse.threadId, message: ":heavy_check_mark: ${env.STAGE_NAME} completed")
            }
            failure {
              slackSend(channel: slackResponse.threadId, 
                      color: "#FF0000", 
                      message: ":x: ${env.STAGE_NAME} failed")
            }
          }
        }
stage('Push To Prod GPU Node') {
    when {
            branch "master"
          }
    stages {
      stage('Push To Prod GPU Node - Bphdp107') {
        steps{
            script {
              withCredentials([usernamePassword(credentialsId: 'bphdp107-spark-app-user-creds', passwordVariable: 'sshPwd', usernameVariable: 'userName')]){
              def remote = [:]
              remote.name = 'bphdp107'
              remote.host = 'bphdp107.corp.instawares.com'
              remote.user = userName
              remote.password = sshPwd
              remote.allowAnyHosts = true
   
              def git_path = "https://${env.JENKINS_GIT_CREDS}@bvhub01.corp.instawares.com/DataSci/MyAssistant.git"
              sshCommand remote: remote, command: """
cd /home/spark_app_user/projects
if [ ! -d MyAssistant ]; then git clone $git_path; fi
cd MyAssistant
git pull
git log --pretty=format:'%H' -n 1 HEAD
""" // wont work unless you remove all whitespace before each line
        }}}
        post {
            success {
              slackSend(channel: slackResponse.threadId, message: ":heavy_check_mark: ${env.STAGE_NAME} completed")
            }
            failure {
              slackSend(channel: slackResponse.threadId,
                      color: "#FF0000",
                      message: ":x: ${env.STAGE_NAME} failed")
            }
          }
      }
      stage('Push To Prod GPU Node - Bphdp109') {
        steps{
            script {
              withCredentials([usernamePassword(credentialsId: 'bphdp109-spark-app-user-creds', passwordVariable: 'sshPwd', usernameVariable: 'userName')]){
              def remote = [:]
              remote.name = 'bphdp109'
              remote.host = 'bphdp109.corp.instawares.com'
              remote.user = userName
              remote.password = sshPwd
              remote.allowAnyHosts = true
   
              def git_path = "https://${env.JENKINS_GIT_CREDS}@bvhub01.corp.instawares.com/DataSci/MyAssistant.git"
              sshCommand remote: remote, command: """
cd /home/spark_app_user/projects
if [ ! -d MyAssistant ]; then git clone $git_path; fi
cd MyAssistant
git pull
git log --pretty=format:'%H' -n 1 HEAD
""" // wont work unless you remove all whitespace before each line
        }}}
        post {
            success {
              slackSend(channel: slackResponse.threadId, message: ":heavy_check_mark: ${env.STAGE_NAME} completed")
            }
            failure {
              slackSend(channel: slackResponse.threadId,
                      color: "#FF0000",
                      message: ":x: ${env.STAGE_NAME} failed")
            }
          }
      }
    }
}

}
  post {
    success {
      slackSend(channel: slackResponse.threadId, 
                color: '#00FF00', 
                message: ":heavy_check_mark: SUCCESSFUL: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL}) completed successfully", 
                replyBroadcast: true)
    }
    failure {
      slackSend(channel: slackResponse.threadId, 
                color: "#FF0000", 
                message: ":x: FAILED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL}) failed", 
                replyBroadcast: true)
    }
  }
}