pluginManagement {
    repositories {
        google()
        maven { url = uri("https://maven.google.com") }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        maven { url = uri("https://maven.google.com") }
        mavenCentral()
    }
}

rootProject.name = "BirdPath"
include(":app")
