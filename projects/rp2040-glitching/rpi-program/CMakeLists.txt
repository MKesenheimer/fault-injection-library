cmake_minimum_required(VERSION 3.12)

set(PICO_SDK_FETCH_FROM_GIT on)
include(pico_sdk_import.cmake)


project(rpi-test
        LANGUAGES ASM C CXX
        VERSION 1.0
        DESCRIPTION "rpi-test"
)


# set(CMAKE_C_STANDARD 11)
# set(CMAKE_CXX_STANDARD 19)


set(FILE_ELF ${CMAKE_PROJECT_NAME}.elf)
set(FILE_HEX ${CMAKE_PROJECT_NAME}.hex)


# Initialize the SDK
pico_sdk_init()


add_executable(${CMAKE_PROJECT_NAME}
    main.cpp
)

target_sources(${CMAKE_PROJECT_NAME}
    PUBLIC
)

target_include_directories(${CMAKE_PROJECT_NAME}
    PUBLIC
        ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(${CMAKE_PROJECT_NAME}
  pico_stdlib
)

pico_add_extra_outputs(${CMAKE_PROJECT_NAME})

# enable usb output, disable uart output
pico_enable_stdio_usb(${CMAKE_PROJECT_NAME} 1)
pico_enable_stdio_uart(${CMAKE_PROJECT_NAME} 0)

# add flash target (make flash)
add_custom_target(flash DEPENDS ${PROJECT_NAME}.elf)
add_custom_command(TARGET flash
    USES_TERMINAL
    COMMAND openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000" -c "program ${PROJECT_NAME}.elf verify reset exit")

# add debug target (make debug)
#set(CMAKE_C_GDB ${GCC_PATH}/arm-none-eabi-gdb CACHE PATH "" FORCE)
add_custom_target(debug DEPENDS ${PROJECT_NAME}.elf)
add_custom_command(TARGET debug
    USES_TERMINAL
    COMMAND openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000")